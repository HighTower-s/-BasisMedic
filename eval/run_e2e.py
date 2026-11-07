"""Run one end-to-end triage configuration (the full agent, or a named baseline per
research.md R-08) over one split -> eval/results/E4_{config_slug}_{split}.json
(data-model.md § 5, contracts/file-formats.md § 3)."""

import argparse
import json

from app import config
from app.agent.formatter import REPAIR_ATTEMPTS
from app.retrieval.store import Store
from app.triage_service import triage
from eval.schema import EvalCase, load_split

RESULTS_DIR = config.ROOT / "eval" / "results"


def category_accuracy(cases: list[dict]) -> float:
    if not cases:
        return 0.0
    return sum(1 for c in cases if c["category_correct"]) / len(cases)


def tcode_recall(cases: list[dict]) -> float:
    """Averaged over in-scope cases only (those with non-empty gold_tcodes) -- an
    out-of-scope case has no gold T-codes to recall (docs/prepare/09_eval_plan.md § 2)."""
    in_scope = [c for c in cases if c["gold_tcodes"]]
    if not in_scope:
        return 0.0
    return sum(c["tcode_recall"] for c in in_scope) / len(in_scope)


def unverified_claim_rate(cases: list[dict]) -> float:
    if not cases:
        return 0.0
    return sum(1 for c in cases if c["unverified_claim"]) / len(cases)


def valid_output_rate(cases: list[dict]) -> float:
    if not cases:
        return 0.0
    return sum(1 for c in cases if not c["fell_back"]) / len(cases)


def _case_tcode_recall(gold_tcodes: list[str], produced_tcodes: list[str]) -> float:
    if not gold_tcodes:
        return 0.0
    return len(set(gold_tcodes) & set(produced_tcodes)) / len(gold_tcodes)


def _agg(cases: list[dict]) -> dict:
    return {
        "category_accuracy": category_accuracy(cases),
        "tcode_recall": tcode_recall(cases),
        "unverified_claim_rate": unverified_claim_rate(cases),
        "valid_output_rate": valid_output_rate(cases),
    }


def _run_one_case(case: EvalCase, *, mode: str, store: Store) -> dict:
    outcome: dict = {}
    result = triage(case.log, mode=mode, store=store, outcome=outcome)
    return {
        "case_id": case.id,
        "difficulty": case.difficulty,
        "format": case.format,
        "gold_category": case.gold_category,
        "gold_tcodes": case.gold_tcodes,
        "produced": result.model_dump(),
        "repaired": outcome.get("repaired", False),
        "fell_back": outcome.get("fell_back", False),
        "category_correct": result.category == case.gold_category,
        "tcode_recall": _case_tcode_recall(case.gold_tcodes, result.tcodes),
        "unverified_claim": bool(result.unverified_tcodes) or outcome.get("citation_dropped", False),
    }


def run_config(*, split: str, mode: str, name: str, store: Store | None = None) -> dict:
    store = store or Store.load()
    cases = load_split(split)
    case_results = [_run_one_case(case, mode=mode, store=store) for case in cases]

    in_scope = [cr for cr, c in zip(case_results, cases) if c.is_in_scope]
    oos = [cr for cr, c in zip(case_results, cases) if c.is_out_of_scope]

    by_difficulty = {}
    for diff in ("easy", "medium", "hard"):
        subset = [cr for cr, c in zip(case_results, cases) if c.is_in_scope and c.difficulty == diff]
        by_difficulty[diff] = _agg(subset)
    thai_subset = [cr for cr, c in zip(case_results, cases) if c.is_in_scope and c.format == "chat_thai"]
    by_difficulty["thai"] = _agg(thai_subset)
    mixed_subset = [cr for cr, c in zip(case_results, cases) if len(c.gold_docs) >= 2]
    by_difficulty["mixed"] = _agg(mixed_subset)
    by_difficulty["oos"] = _agg(oos) if oos else {}

    return {
        "config": {
            "experiment": "E4",
            "name": name,
            "split": split,
            "baseline": mode,
            "max_steps": config.max_steps(),
            "repair_attempts": REPAIR_ATTEMPTS,
            "chat_model": config.chat_model(),
            "corpus_sha": store.manifest.corpus_sha,
            "git_commit": store.manifest.git_commit,
        },
        "aggregate": {
            "n_cases": len(case_results),
            **_agg(case_results),
            "by_difficulty": by_difficulty,
        },
        "cases": case_results,
    }


def config_slug(mode: str) -> str:
    return mode


def classify_e2e_failure(case_result: dict) -> str | None:
    """None means not a failure. Checked in this order: fallback (repair exhausted,
    data-model.md FailureTypeE2E) outranks a wrong category, which outranks a T-code
    recall miss, which outranks an otherwise-unverified claim. shortcut: loop_exhausted
    and schema_invalid_after_fallback aren't separately distinguished from
    repair_exhausted with the outcome tracking triage() currently exposes -- upgrade by
    having triage()'s outcome dict record which bound was actually hit, if that
    distinction becomes worth reporting."""
    if case_result["fell_back"]:
        return "repair_exhausted"
    if not case_result["category_correct"]:
        return "category_wrong"
    if case_result["gold_tcodes"] and case_result["tcode_recall"] < 1.0:
        return "tcode_recall_miss"
    if case_result["unverified_claim"]:
        return "unverified_claim"
    return None


def build_e4_failure_records(case_results: list[dict], config_name: str) -> list[dict]:
    records = []
    for cr in case_results:
        failure_type = classify_e2e_failure(cr)
        if failure_type is None:
            continue
        records.append(
            {
                "case_id": cr["case_id"],
                "config_name": config_name,
                "expected_category": cr["gold_category"],
                "produced_category": cr["produced"]["category"],
                "expected_tcodes": cr["gold_tcodes"],
                "produced_tcodes": cr["produced"]["tcodes"],
                "unverified_tcodes": cr["produced"]["unverified_tcodes"],
                "failure_type": failure_type,
                "note": "",
            }
        )
    return records


def write_result(result: dict, split: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cfg = result["config"]
    slug = config_slug(cfg["baseline"])
    path = RESULTS_DIR / f"{cfg['experiment']}_{slug}_{split}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("dev", "test"), required=True)
    parser.add_argument("--mode", choices=("agent", "E-NoRAG", "E-ClassicRAG"), required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args(argv)

    result = run_config(split=args.split, mode=args.mode, name=args.name)
    write_result(result, args.split)
    agg = result["aggregate"]
    print(
        f"{args.name}: category_accuracy={agg['category_accuracy']:.3f} "
        f"tcode_recall={agg['tcode_recall']:.3f} "
        f"unverified_claim_rate={agg['unverified_claim_rate']:.3f} "
        f"valid_output_rate={agg['valid_output_rate']:.3f}"
    )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
