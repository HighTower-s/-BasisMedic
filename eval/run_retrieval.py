"""Run one retrieval configuration over one split -> eval/results/{experiment}_{slug}.json
(R-11, data-model.md § 9, contracts/file-formats.md § 8)."""

import argparse
import json

from app import config
from app.retrieval.search import rank, search
from app.retrieval.store import Store
from eval.metrics import false_refusal_rate, gate_accuracy, mrr, recall_at_k
from eval.schema import load_split

RESULTS_DIR = config.ROOT / "eval" / "results"


def _agg_recall(results: list[dict]) -> dict:
    if not results:
        return {"recall_at_3_pre": 0.0, "mrr_pre": 0.0, "recall_at_3_post": 0.0, "mrr_post": 0.0}
    n = len(results)
    return {
        "recall_at_3_pre": sum(r["recall_at_k_pre"] for r in results) / n,
        "mrr_pre": sum(r["rr_pre"] for r in results) / n,
        "recall_at_3_post": sum(r["recall_at_k_post"] for r in results) / n,
        "mrr_post": sum(r["rr_post"] for r in results) / n,
    }


def assert_resolvable_citations(case_results: list[dict], store: Store) -> None:
    """Every returned chunk_id must resolve to real corpus text (FR-010, SC-005)."""
    known_ids = {c.chunk_id for c in store.chunks}
    for cr in case_results:
        for item in cr["retrieved"]:
            if item["chunk_id"] not in known_ids:
                raise AssertionError(
                    f"case {cr['case_id']}: chunk_id {item['chunk_id']!r} does not resolve "
                    "to any chunk in the loaded index"
                )


def run_config(
    *,
    split: str,
    mode: str,
    chunk_strategy: str,
    min_score: float,
    experiment: str,
    name: str,
    k: int = 3,
    store: Store | None = None,
) -> dict:
    store = store or Store.load()
    if store.manifest.chunk_strategy != chunk_strategy:
        raise ValueError(
            f"index was built with chunk_strategy={store.manifest.chunk_strategy!r}, but "
            f"this run requested {chunk_strategy!r}; re-ingest with --strategy {chunk_strategy}"
        )

    cases = load_split(split)
    case_results = []

    for case in cases:
        ranked = rank(case.log, mode=mode, store=store)
        pre_docs: list[str] = []
        for hit in ranked:
            if hit.doc_id not in pre_docs:
                pre_docs.append(hit.doc_id)
        pre_docs = pre_docs[:k]

        gated = search(case.log, mode=mode, k=k, min_score=min_score, store=store)
        post_docs = [h.doc_id for h in gated]
        gated_out = len(gated) == 0

        if case.is_in_scope:
            recall_pre = recall_at_k(pre_docs, case.gold_docs)
            recall_post = recall_at_k(post_docs, case.gold_docs)
            rr_pre = mrr(pre_docs, case.gold_docs)
            rr_post = mrr(post_docs, case.gold_docs)
            correct_gate = not gated_out
        else:
            recall_pre = recall_post = rr_pre = rr_post = None
            correct_gate = gated_out

        case_results.append(
            {
                "_case": case,
                "case_id": case.id,
                "difficulty": case.difficulty,
                "format": case.format,
                "retrieved": [
                    {
                        "doc_id": h.doc_id,
                        "chunk_id": h.chunk_id,
                        "score": h.score_for(mode),
                        "rank": h.rank,
                    }
                    for h in gated
                ],
                "gated_out": gated_out,
                "recall_at_k_pre": recall_pre,
                "recall_at_k_post": recall_post,
                "rr_pre": rr_pre,
                "rr_post": rr_post,
                "correct_gate": correct_gate,
            }
        )

    in_scope_results = [cr for cr in case_results if cr["_case"].is_in_scope]
    oos_results = [cr for cr in case_results if cr["_case"].is_out_of_scope]

    by_difficulty = {}
    for diff in ("easy", "medium", "hard"):
        subset = [cr for cr in in_scope_results if cr["_case"].difficulty == diff]
        by_difficulty[diff] = _agg_recall(subset)
    thai_subset = [cr for cr in in_scope_results if cr["_case"].format == "chat_thai"]
    by_difficulty["thai"] = _agg_recall(thai_subset)
    mixed_subset = [cr for cr in in_scope_results if len(cr["_case"].gold_docs) >= 2]
    by_difficulty["mixed"] = _agg_recall(mixed_subset)
    by_difficulty["oos"] = (
        {"gate_accuracy": gate_accuracy([cr["gated_out"] for cr in oos_results])}
        if oos_results
        else {}
    )

    aggregate = {
        "n_in_scope": len(in_scope_results),
        "n_out_of_scope": len(oos_results),
        **_agg_recall(in_scope_results),
        "oos_gate_accuracy": gate_accuracy([cr["gated_out"] for cr in oos_results]),
        "false_refusal_rate": false_refusal_rate([cr["gated_out"] for cr in in_scope_results]),
        "by_difficulty": by_difficulty,
    }

    for cr in case_results:
        del cr["_case"]

    assert_resolvable_citations(case_results, store)

    return {
        "config": {
            "experiment": experiment,
            "name": name,
            "split": split,
            "mode": mode,
            "chunk_strategy": chunk_strategy,
            "k": k,
            "min_score": min_score,
            "embed_model": store.manifest.embed_model,
            "corpus_sha": store.manifest.corpus_sha,
            "git_commit": store.manifest.git_commit,
        },
        "aggregate": aggregate,
        "cases": case_results,
    }


def config_slug(mode: str, chunk_strategy: str, k: int, min_score: float) -> str:
    return f"{mode}-{chunk_strategy}-k{k}-ms{int(round(min_score * 100)):02d}"


def write_result(result: dict, split: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cfg = result["config"]
    slug = config_slug(cfg["mode"], cfg["chunk_strategy"], cfg["k"], cfg["min_score"])
    path = RESULTS_DIR / f"{cfg['experiment']}_{slug}_{split}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("dev", "test"), required=True)
    parser.add_argument("--mode", choices=("dense", "bm25", "hybrid"), required=True)
    parser.add_argument("--strategy", choices=("section", "fixed"), required=True)
    parser.add_argument("--min-score", type=float, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--experiment", default="adhoc")
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args(argv)

    result = run_config(
        split=args.split,
        mode=args.mode,
        chunk_strategy=args.strategy,
        min_score=args.min_score,
        experiment=args.experiment,
        name=args.name,
        k=args.k,
    )
    write_result(result, args.split)
    agg = result["aggregate"]
    print(
        f"{args.name}: recall@3 pre={agg['recall_at_3_pre']:.3f} post={agg['recall_at_3_post']:.3f} "
        f"mrr pre={agg['mrr_pre']:.3f} post={agg['mrr_post']:.3f} "
        f"oos_gate_accuracy={agg['oos_gate_accuracy']:.3f} false_refusal_rate={agg['false_refusal_rate']:.3f}"
    )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
