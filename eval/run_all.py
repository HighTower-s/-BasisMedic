"""Run every experiment -> eval/results/results.md (FR-031, FR-037, FR-038, FR-039, SC-004).

E1: naive fixed-800/150 vs section-aligned chunking, mode=dense, pre-gate.
E2: bm25 vs dense vs hybrid on E1's winner, pre-gate, against named baselines R-BM25
    and R-Dense-naive.
E3: MIN_SCORE sweep on the dev split only (Phase 7).
"""

from datetime import datetime, timezone
from pathlib import Path

from app import config
from app.retrieval.ingest import build_index
from app.retrieval.store import Store
from eval.run_retrieval import run_config, write_result

INDEX_DIRS = {
    "section": config.ROOT / "data" / "index",
    "fixed": config.ROOT / "data" / "index_fixed",
}

MIN_SCORE_DEFAULT = 0.40
RESULTS_MD = config.ROOT / "eval" / "results" / "results.md"


def get_store(strategy: str, embed: bool = True) -> Store:
    index_dir = INDEX_DIRS[strategy]
    if not (index_dir / "manifest.json").exists():
        build_index(strategy=strategy, embed=embed, index_dir=index_dir)
    return Store.load(index_dir=index_dir)


def _assert_comparable(rows: list[dict]) -> None:
    """A comparison table's rows must share split and corpus_sha, or the comparison is
    meaningless (data-model.md § 10)."""
    splits = {r["config"]["split"] for r in rows}
    shas = {r["config"]["corpus_sha"] for r in rows}
    if len(splits) > 1:
        raise ValueError(f"comparison rows span multiple splits: {sorted(splits)}")
    if len(shas) > 1:
        raise ValueError(f"comparison rows span multiple corpus_sha values: {sorted(shas)}")


def run_e1() -> dict[str, list[dict]]:
    """fixed-800/150 vs section, mode=dense, k=3, pre-gate (FR-037). Returns {split: [rows]}."""
    by_split: dict[str, list[dict]] = {"dev": [], "test": []}
    for strategy in ("fixed", "section"):
        store = get_store(strategy)
        for split in ("dev", "test"):
            result = run_config(
                split=split, mode="dense", chunk_strategy=strategy, min_score=MIN_SCORE_DEFAULT,
                experiment="E1", name=f"dense + {strategy}", k=3, store=store,
            )
            write_result(result, split)
            by_split[split].append(result)
    for rows in by_split.values():
        _assert_comparable(rows)
    return by_split


def pick_winner_from_dev(e1_dev_rows: list[dict]) -> str:
    """Chosen from the DEV split only — the test split never informs a tuning decision
    (Constitution I)."""
    best = max(e1_dev_rows, key=lambda r: r["aggregate"]["recall_at_3_pre"])
    return best["config"]["chunk_strategy"]


def run_e2(winning_strategy: str) -> tuple[dict[str, list[dict]], dict[str, dict[str, dict]]]:
    """bm25 / dense / hybrid on the E1 winner, pre-gate (FR-038). R-BM25 and
    R-Dense-naive are the two named baselines, run regardless of which strategy won E1.
    Baselines are kept per split — a dev row must never be compared against a test-split
    baseline number (R-01/R-08: never mix case populations across splits)."""
    by_split: dict[str, list[dict]] = {"dev": [], "test": []}
    winner_store = get_store(winning_strategy)
    for mode in ("bm25", "dense", "hybrid"):
        for split in ("dev", "test"):
            result = run_config(
                split=split, mode=mode, chunk_strategy=winning_strategy, min_score=MIN_SCORE_DEFAULT,
                experiment="E2", name=f"{mode} + {winning_strategy}", k=3, store=winner_store,
            )
            write_result(result, split)
            by_split[split].append(result)

    baselines: dict[str, dict[str, dict]] = {"R-BM25": {}, "R-Dense-naive": {}}
    for split in ("dev", "test"):
        baselines["R-BM25"][split] = next(
            r for r in by_split[split] if r["config"]["mode"] == "bm25"
        )

    fixed_store = get_store("fixed")
    for split in ("dev", "test"):
        result = run_config(
            split=split, mode="dense", chunk_strategy="fixed", min_score=MIN_SCORE_DEFAULT,
            experiment="E2", name="R-Dense-naive", k=3, store=fixed_store,
        )
        write_result(result, split)
        baselines["R-Dense-naive"][split] = result

    for rows in by_split.values():
        _assert_comparable(rows)
    return by_split, baselines


def _render_e1_table(rows: list[dict], winning_strategy: str) -> str:
    lines = [
        "### E1 — Chunking strategy (pre-gate, mode=dense, k=3)",
        "",
        "Varied variable: `chunk_strategy`. Baseline: `fixed` (naive 800/150).",
        "",
        "| split | chunk_strategy | recall@3_pre | Δ vs fixed | mrr_pre | Δ vs fixed |",
        "|---|---|---|---|---|---|",
    ]
    by_strategy_split = {(r["config"]["chunk_strategy"], r["config"]["split"]): r for r in rows}
    for split in ("dev", "test"):
        baseline = by_strategy_split[("fixed", split)]["aggregate"]
        for strategy in ("fixed", "section"):
            agg = by_strategy_split[(strategy, split)]["aggregate"]
            d_recall = agg["recall_at_3_pre"] - baseline["recall_at_3_pre"]
            d_mrr = agg["mrr_pre"] - baseline["mrr_pre"]
            lines.append(
                f"| {split} | {strategy} | {agg['recall_at_3_pre']:.3f} | {d_recall:+.3f} | "
                f"{agg['mrr_pre']:.3f} | {d_mrr:+.3f} |"
            )
    lines.append("")
    lines.append(f"**Winner (chosen from the dev split only, Constitution I): `{winning_strategy}`.**")
    return "\n".join(lines)


def _render_e2_table(
    rows: list[dict], baselines: dict[str, dict[str, dict]], winning_strategy: str
) -> str:
    lines = [
        f"### E2 — Retrieval mode (pre-gate, chunk_strategy={winning_strategy}, k=3)",
        "",
        "Varied variable: `mode`. Named baselines (FR-038): `R-BM25` (keyword-only) and "
        "`R-Dense-naive` (dense retrieval over naive fixed-800/150 chunks). Deltas are "
        "computed against the baseline measured on the *same* split (R-08: never mix "
        "dev and test populations).",
        "",
        "| split | mode | recall@3_pre | Δ vs R-BM25 | Δ vs R-Dense-naive | mrr_pre | gate note |",
        "|---|---|---|---|---|---|---|",
    ]
    by_mode_split = {(r["config"]["mode"], r["config"]["split"]): r for r in rows}
    for split in ("dev", "test"):
        bm25_base = baselines["R-BM25"][split]["aggregate"]
        dense_naive_base = baselines["R-Dense-naive"][split]["aggregate"]
        for mode in ("bm25", "dense", "hybrid"):
            agg = by_mode_split[(mode, split)]["aggregate"]
            d_bm25 = agg["recall_at_3_pre"] - bm25_base["recall_at_3_pre"]
            d_dense_naive = agg["recall_at_3_pre"] - dense_naive_base["recall_at_3_pre"]
            gate_note = "rare-token rule only (no cosine, R-02)" if mode == "bm25" else "cosine + rare-token"
            lines.append(
                f"| {split} | {mode} | {agg['recall_at_3_pre']:.3f} | {d_bm25:+.3f} | "
                f"{d_dense_naive:+.3f} | {agg['mrr_pre']:.3f} | {gate_note} |"
            )
    lines.append("")
    test_bm25 = baselines["R-BM25"]["test"]["aggregate"]
    test_dense_naive = baselines["R-Dense-naive"]["test"]["aggregate"]
    lines.append(
        f"Baselines, test split: R-BM25 recall@3_pre={test_bm25['recall_at_3_pre']:.3f}, "
        f"R-Dense-naive recall@3_pre={test_dense_naive['recall_at_3_pre']:.3f}."
    )
    return "\n".join(lines)


def _render_header(section_store: Store) -> str:
    manifest = section_store.manifest
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        "# BasisMedic — Retrieval Evaluation Report\n\n"
        f"- corpus_sha: `{manifest.corpus_sha}`\n"
        f"- git commit: `{manifest.git_commit}`\n"
        f"- embed model: `{manifest.embed_model}`\n"
        f"- generated: {now}\n"
        "- splits: dev (10 cases, tuning only), test (30 cases, reporting only)\n"
        "- all case logs are synthetic\n"
    )


def write_results_md(sections: list[str]) -> None:
    RESULTS_MD.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_MD.write_text("\n\n".join(sections) + "\n", encoding="utf-8")


def main() -> int:
    e1_by_split = run_e1()
    winning_strategy = pick_winner_from_dev(e1_by_split["dev"])
    print(f"E1 winner (from dev split): chunk_strategy={winning_strategy}")

    e2_by_split, baselines = run_e2(winning_strategy)
    for split, rows in e2_by_split.items():
        for row in rows:
            agg = row["aggregate"]
            print(
                f"E2 {split} {row['config']['name']}: recall@3_pre={agg['recall_at_3_pre']:.3f} "
                f"mrr_pre={agg['mrr_pre']:.3f}"
            )

    section_store = get_store("section")
    sections = [
        _render_header(section_store),
        _render_e1_table(e1_by_split["dev"] + e1_by_split["test"], winning_strategy),
        _render_e2_table(e2_by_split["dev"] + e2_by_split["test"], baselines, winning_strategy),
    ]
    write_results_md(sections)
    print(f"wrote {RESULTS_MD}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
