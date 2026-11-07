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
from app.retrieval.store import StaleIndexError, Store
from eval.run_e2e import build_e4_failure_records
from eval.run_e2e import run_config as run_e2e_config
from eval.run_e2e import write_result as write_e2e_result
from eval.run_retrieval import (
    append_failures,
    build_failure_records,
    run_config,
    truncate_failures,
    write_result,
)

INDEX_DIRS = {
    "section": config.ROOT / "data" / "index_section",
    "fixed": config.ROOT / "data" / "index_fixed",
}

MIN_SCORE_DEFAULT = 0.40
RESULTS_MD = config.ROOT / "eval" / "results" / "results.md"


def get_store(strategy: str, embed: bool = True) -> Store:
    """Builds the experiment index on first use, and rebuilds it if the corpus has
    moved on since (StaleIndexError) rather than failing the whole experiment run."""
    index_dir = INDEX_DIRS[strategy]
    if not (index_dir / "manifest.json").exists():
        build_index(strategy=strategy, embed=embed, index_dir=index_dir)
    try:
        return Store.load(index_dir=index_dir)
    except StaleIndexError:
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


_MODE_PREFERENCE = ("hybrid", "dense", "bm25")


def pick_mode_from_dev(e2_dev_rows: list[dict]) -> str:
    """Chosen from the DEV split only (Constitution I). On a tie — expected here, since
    the 8-case dev split gives all three modes recall@3_pre=1.0 (a ceiling effect) —
    prefer hybrid, then dense, then bm25, reflecting the project's own retrieval-quality
    ordering rather than an arbitrary dict/list order."""
    def key(row: dict) -> tuple:
        agg = row["aggregate"]
        mode = row["config"]["mode"]
        return (agg["recall_at_3_pre"], agg["mrr_pre"], -_MODE_PREFERENCE.index(mode))

    return max(e2_dev_rows, key=key)["config"]["mode"]


SWEEP_FLOORS = [round(0.30 + 0.05 * i, 2) for i in range(7)]  # 0.30 .. 0.60


def sweep_min_score(
    split: str, *, mode: str, chunk_strategy: str, store: Store | None = None
) -> list[dict]:
    """E3: sweep MIN_SCORE on the dev split ONLY, post-gate (FR-039). Raises for any
    split other than 'dev' — the test set must stay mechanically out of reach of tuning
    (FR-041, SC-009)."""
    if split != "dev":
        raise ValueError(f"sweep_min_score only accepts split='dev', got {split!r} (FR-041)")
    store = store or get_store(chunk_strategy)
    rows = []
    for floor in SWEEP_FLOORS:
        result = run_config(
            split="dev", mode=mode, chunk_strategy=chunk_strategy, min_score=floor,
            experiment="E3", name=f"sweep min_score={floor}", k=3, store=store,
        )
        write_result(result, "dev")
        rows.append(result)
    return rows


def choose_min_score(sweep_rows: list[dict]) -> dict:
    """Maximise in-scope recall@3_post + out-of-scope gate accuracy; on a tie prefer the
    smaller floor (keeps more in-scope recall). Returns the winning sweep row."""
    def key(row: dict) -> tuple:
        agg = row["aggregate"]
        return (agg["recall_at_3_post"] + agg["oos_gate_accuracy"], -row["config"]["min_score"])

    return max(sweep_rows, key=key)


def run_e4() -> list[dict]:
    """Full agent vs E-NoRAG vs E-ClassicRAG, test split (FR-016, FR-018, R-08). All
    three pass through the identical triage()/verify.py pipeline -- no baseline is
    measured leniently."""
    rows = []
    for mode in ("agent", "E-NoRAG", "E-ClassicRAG"):
        result = run_e2e_config(split="test", mode=mode, name=mode)
        write_e2e_result(result, "test")
        rows.append(result)
    _assert_comparable(rows)
    return rows


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


def _render_e3_table(sweep_rows: list[dict], chosen: dict, sweep_name: str) -> str:
    lines = [
        "### E3 — MIN_SCORE sweep (dev split only, post-gate)",
        "",
        f"Experiment id: `{sweep_name}`. In-scope recall@3 and out-of-scope rejection rate "
        "traded off across the floor. **Dev cases only — the test set is never read here** "
        "(FR-041).",
        "",
        "| min_score | recall@3_post (in-scope) | oos_gate_accuracy | false_refusal_rate |",
        "|---|---|---|---|",
    ]
    for row in sweep_rows:
        agg = row["aggregate"]
        marker = "  <- chosen" if row["config"]["min_score"] == chosen["config"]["min_score"] else ""
        lines.append(
            f"| {row['config']['min_score']:.2f} | {agg['recall_at_3_post']:.3f} | "
            f"{agg['oos_gate_accuracy']:.3f} | {agg['false_refusal_rate']:.3f}{marker} |"
        )
    lines.append("")
    lines.append(
        f"**Chosen MIN_SCORE = {chosen['config']['min_score']:.2f}**, from dev sweep "
        f"`{sweep_name}` (maximises recall@3_post + oos_gate_accuracy; ties broken toward "
        "the smaller floor)."
    )
    return "\n".join(lines)


def _render_headline_table(test_result: dict) -> str:
    agg = test_result["aggregate"]
    cfg = test_result["config"]
    lines = [
        "### Headline — final configuration on the test set (post-gate)",
        "",
        f"mode=`{cfg['mode']}`, chunk_strategy=`{cfg['chunk_strategy']}`, k={cfg['k']}, "
        f"min_score={cfg['min_score']:.2f} (unchanged from the E3 dev sweep).",
        "",
        "| metric | value |",
        "|---|---|",
        f"| recall@3 (post-gate) | {agg['recall_at_3_post']:.3f} |",
        f"| MRR (post-gate) | {agg['mrr_post']:.3f} |",
        f"| out-of-scope gate accuracy | {agg['oos_gate_accuracy']:.3f} |",
        f"| false refusal rate | {agg['false_refusal_rate']:.3f} |",
        "",
        "Per-difficulty slices (post-gate recall@3):",
        "",
        "| slice | recall@3_post | mrr_post |",
        "|---|---|---|",
    ]
    for slice_name in ("easy", "medium", "hard", "thai", "mixed"):
        s = agg["by_difficulty"].get(slice_name, {})
        if "recall_at_3_post" in s:
            lines.append(f"| {slice_name} | {s['recall_at_3_post']:.3f} | {s['mrr_post']:.3f} |")
    oos = agg["by_difficulty"].get("oos", {})
    if "gate_accuracy" in oos:
        lines.append(f"| out-of-scope | gate_accuracy={oos['gate_accuracy']:.3f} | - |")
    return "\n".join(lines)


def _render_verdict_and_limitations(e2_rows_test: list[dict], baselines: dict, n_failures: int) -> str:
    hybrid_row = next(r for r in e2_rows_test if r["config"]["mode"] == "hybrid")
    hybrid_recall = hybrid_row["aggregate"]["recall_at_3_pre"]
    bm25_recall = baselines["R-BM25"]["test"]["aggregate"]["recall_at_3_pre"]
    dense_naive_recall = baselines["R-Dense-naive"]["test"]["aggregate"]["recall_at_3_pre"]
    beats_both = hybrid_recall > bm25_recall and hybrid_recall > dense_naive_recall
    verdict = (
        f"Hybrid retrieval ({hybrid_recall:.3f} recall@3 pre-gate, test split) "
        + (
            f"beats both named baselines (R-BM25={bm25_recall:.3f}, "
            f"R-Dense-naive={dense_naive_recall:.3f})."
            if beats_both
            else (
                f"does **not** beat both named baselines (R-BM25={bm25_recall:.3f}, "
                f"R-Dense-naive={dense_naive_recall:.3f}) — stated plainly, not hidden (FR-044)."
            )
        )
    )
    return (
        "### Verdict\n\n"
        f"{verdict}\n\n"
        f"`eval/results/failures.jsonl` records {n_failures} failing test case(s) for the "
        "final headline configuration, each with expected-vs-retrieved detail and a "
        "failure type.\n\n"
        "### Limitations\n\n"
        "- All case logs are **synthetic**, written by the author to resemble real SAP "
        "Basis error formats — not sampled from a production system.\n"
        "- The corpus covers 16 runbooks across 8 incident categories; any incident "
        "outside those categories, or any incident this corpus simply does not "
        "describe, has no chance of a correct answer regardless of retrieval quality.\n"
        "- Single-author bias: runbook content, the eval-case labels, and the "
        "difficulty tiers were all written by one person, who may unconsciously write "
        "eval queries that resemble their own runbook phrasing more than a real "
        "incident would.\n"
        "- The `[A-Za-z0-9_/]+` BM25 tokenizer cannot segment Thai text (no inter-word "
        "spaces), so Thai queries contribute **zero** BM25 tokens — the Thai slice in "
        "the headline table is carried entirely by the dense/embedding side "
        "(research.md R-05).\n"
    )


def _render_e4_table(rows: list[dict]) -> str:
    lines = [
        "### E4 — End-to-end comparison (test split)",
        "",
        "Varied variable: evidence-gathering strategy. `E-NoRAG` = no retrieval at all; "
        "`E-ClassicRAG` = exactly one non-agentic search call; `agent` = the full bounded "
        "tool-calling loop. All three pass through the identical `verify.py` checks "
        "(research.md R-08) — no baseline is measured leniently.",
        "",
        "| config | category_accuracy | tcode_recall | unverified_claim_rate | valid_output_rate |",
        "|---|---|---|---|---|",
    ]
    by_mode = {r["config"]["baseline"]: r for r in rows}
    for mode in ("E-NoRAG", "E-ClassicRAG", "agent"):
        agg = by_mode[mode]["aggregate"]
        lines.append(
            f"| {mode} | {agg['category_accuracy']:.3f} | {agg['tcode_recall']:.3f} | "
            f"{agg['unverified_claim_rate']:.3f} | {agg['valid_output_rate']:.3f} |"
        )
    agent_agg = by_mode["agent"]["aggregate"]
    norag_agg = by_mode["E-NoRAG"]["aggregate"]
    classic_agg = by_mode["E-ClassicRAG"]["aggregate"]
    beats_both = (
        agent_agg["category_accuracy"] > norag_agg["category_accuracy"]
        and agent_agg["category_accuracy"] > classic_agg["category_accuracy"]
    )
    verdict = (
        f"Full agent category_accuracy={agent_agg['category_accuracy']:.3f} vs "
        f"E-NoRAG={norag_agg['category_accuracy']:.3f}, E-ClassicRAG={classic_agg['category_accuracy']:.3f}. "
        + (
            "Beats both baselines."
            if beats_both
            else "Does **not** beat both baselines — stated plainly (FR-022)."
        )
    )
    lines.append("")
    lines.append(verdict)
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


def _update_env_example_defaults(mode: str, chunk_strategy: str, min_score: float) -> None:
    """Sync .env.example's shipped defaults to the measured winners (FR-040, SC-009) —
    leaving a stale CHUNK_STRATEGY/RETRIEVAL_MODE here would silently contradict the
    E1/E2 tables this same run just wrote."""
    path = config.ROOT / ".env.example"
    replacements = {
        "RETRIEVAL_MODE=": f"RETRIEVAL_MODE={mode}\n",
        "CHUNK_STRATEGY=": f"CHUNK_STRATEGY={chunk_strategy}\n",
        "MIN_SCORE=": f"MIN_SCORE={min_score:.2f}\n",
    }
    out = []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        for prefix, new_line in replacements.items():
            if line.startswith(prefix):
                line = new_line
                break
        out.append(line)
    path.write_text("".join(out), encoding="utf-8")


def main() -> int:
    truncate_failures()  # FR-043: always created, truncated once per run_all invocation

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

    winning_mode = pick_mode_from_dev(e2_by_split["dev"])
    print(f"E2 winner (from dev split): mode={winning_mode}")

    winner_store = get_store(winning_strategy)
    sweep_name = f"E3-{winning_mode}-{winning_strategy}"
    sweep_rows = sweep_min_score(
        "dev", mode=winning_mode, chunk_strategy=winning_strategy, store=winner_store
    )
    chosen = choose_min_score(sweep_rows)
    chosen_floor = chosen["config"]["min_score"]
    print(f"E3 chosen MIN_SCORE (from dev sweep {sweep_name}): {chosen_floor:.2f}")

    headline = run_config(
        split="test", mode=winning_mode, chunk_strategy=winning_strategy, min_score=chosen_floor,
        experiment="headline", name=f"{winning_mode} + {winning_strategy} (final)", k=3,
        store=winner_store,
    )
    write_result(headline, "test")

    failure_records = build_failure_records("test", headline["cases"], headline["config"]["name"])
    append_failures(failure_records)
    print(f"failures.jsonl: {len(failure_records)} failing case(s) for the headline config")

    _update_env_example_defaults(winning_mode, winning_strategy, chosen_floor)

    e4_rows = run_e4()
    by_mode = {r["config"]["baseline"]: r for r in e4_rows}
    e4_failure_records = build_e4_failure_records(by_mode["agent"]["cases"], "agent")
    append_failures(e4_failure_records)
    print(f"failures.jsonl: +{len(e4_failure_records)} e2e failing case(s) for the agent config")
    print(
        f"E4 agent: category_accuracy={by_mode['agent']['aggregate']['category_accuracy']:.3f} "
        f"tcode_recall={by_mode['agent']['aggregate']['tcode_recall']:.3f}"
    )

    section_store = get_store("section")
    sections = [
        _render_header(section_store),
        _render_e1_table(e1_by_split["dev"] + e1_by_split["test"], winning_strategy),
        _render_e2_table(e2_by_split["dev"] + e2_by_split["test"], baselines, winning_strategy),
        _render_e3_table(sweep_rows, chosen, sweep_name),
        _render_headline_table(headline),
        _render_e4_table(e4_rows),
        _render_verdict_and_limitations(e2_by_split["test"], baselines, len(failure_records) + len(e4_failure_records)),
    ]
    write_results_md(sections)
    print(f"wrote {RESULTS_MD}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
