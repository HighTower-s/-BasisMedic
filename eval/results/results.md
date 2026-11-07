# BasisMedic — Retrieval Evaluation Report

- corpus_sha: `49b07d941e2b3e4b76a3fa0c7c94a434e6e5d5709952d25cb914acdf65252018`
- git commit: `f06f1e5`
- embed model: `bge-m3`
- generated: 2026-11-07T19:13:16Z
- splits: dev (10 cases, tuning only), test (30 cases, reporting only)
- all case logs are synthetic


### E1 — Chunking strategy (pre-gate, mode=dense, k=3)

Varied variable: `chunk_strategy`. Baseline: `fixed` (naive 800/150).

| split | chunk_strategy | recall@3_pre | Δ vs fixed | mrr_pre | Δ vs fixed |
|---|---|---|---|---|---|
| dev | fixed | 1.000 | +0.000 | 1.000 | +0.000 |
| dev | section | 1.000 | +0.000 | 1.000 | +0.000 |
| test | fixed | 0.942 | +0.000 | 0.923 | +0.000 |
| test | section | 0.904 | -0.038 | 0.904 | -0.019 |

**Winner (chosen from the dev split only, Constitution I): `fixed`.**

### E2 — Retrieval mode (pre-gate, chunk_strategy=fixed, k=3)

Varied variable: `mode`. Named baselines (FR-038): `R-BM25` (keyword-only) and `R-Dense-naive` (dense retrieval over naive fixed-800/150 chunks). Deltas are computed against the baseline measured on the *same* split (R-08: never mix dev and test populations).

| split | mode | recall@3_pre | Δ vs R-BM25 | Δ vs R-Dense-naive | mrr_pre | gate note |
|---|---|---|---|---|---|---|
| dev | bm25 | 1.000 | +0.000 | +0.000 | 0.875 | rare-token rule only (no cosine, R-02) |
| dev | dense | 1.000 | +0.000 | +0.000 | 1.000 | cosine + rare-token |
| dev | hybrid | 1.000 | +0.000 | +0.000 | 1.000 | cosine + rare-token |
| test | bm25 | 0.846 | +0.000 | -0.096 | 0.769 | rare-token rule only (no cosine, R-02) |
| test | dense | 0.942 | +0.096 | +0.000 | 0.923 | cosine + rare-token |
| test | hybrid | 0.962 | +0.115 | +0.019 | 0.904 | cosine + rare-token |

Baselines, test split: R-BM25 recall@3_pre=0.846, R-Dense-naive recall@3_pre=0.942.

### E3 — MIN_SCORE sweep (dev split only, post-gate)

Experiment id: `E3-hybrid-fixed`. In-scope recall@3 and out-of-scope rejection rate traded off across the floor. **Dev cases only — the test set is never read here** (FR-041).

| min_score | recall@3_post (in-scope) | oos_gate_accuracy | false_refusal_rate |
|---|---|---|---|
| 0.30 | 1.000 | 0.000 | 0.000 |
| 0.35 | 1.000 | 0.000 | 0.000 |
| 0.40 | 1.000 | 0.000 | 0.000 |
| 0.45 | 1.000 | 0.000 | 0.000 |
| 0.50 | 1.000 | 0.000 | 0.000 |
| 0.55 | 1.000 | 0.500 | 0.000 |
| 0.60 | 1.000 | 1.000 | 0.000  <- chosen |

**Chosen MIN_SCORE = 0.60**, from dev sweep `E3-hybrid-fixed` (maximises recall@3_post + oos_gate_accuracy; ties broken toward the smaller floor).

### Headline — final configuration on the test set (post-gate)

mode=`hybrid`, chunk_strategy=`fixed`, k=3, min_score=0.60 (unchanged from the E3 dev sweep).

| metric | value |
|---|---|
| recall@3 (post-gate) | 0.808 |
| MRR (post-gate) | 0.788 |
| out-of-scope gate accuracy | 1.000 |
| false refusal rate | 0.154 |

Per-difficulty slices (post-gate recall@3):

| slice | recall@3_post | mrr_post |
|---|---|---|
| easy | 0.875 | 0.875 |
| medium | 1.000 | 1.000 |
| hard | 0.600 | 0.550 |
| thai | 0.667 | 0.500 |
| mixed | 1.000 | 1.000 |
| out-of-scope | gate_accuracy=1.000 | - |

### E4 — End-to-end comparison (test split)

Varied variable: evidence-gathering strategy. `E-NoRAG` = no retrieval at all; `E-ClassicRAG` = exactly one non-agentic search call; `agent` = the full bounded tool-calling loop. All three pass through the identical `verify.py` checks (research.md R-08) — no baseline is measured leniently.

| config | category_accuracy | tcode_recall | unverified_claim_rate | valid_output_rate |
|---|---|---|---|---|
| E-NoRAG | 0.600 | 0.154 | 0.767 | 0.933 |
| E-ClassicRAG | 0.700 | 0.442 | 0.767 | 1.000 |
| agent | 0.567 | 0.365 | 0.467 | 0.967 |

Full agent category_accuracy=0.567 vs E-NoRAG=0.600, E-ClassicRAG=0.700. Does **not** beat both baselines — stated plainly (FR-022).

### Verdict

Hybrid retrieval (0.962 recall@3 pre-gate, test split) beats both named baselines (R-BM25=0.846, R-Dense-naive=0.942).

`eval/results/failures.jsonl` records 31 failing test case(s) for the final headline configuration, each with expected-vs-retrieved detail and a failure type.

### Limitations

- All case logs are **synthetic**, written by the author to resemble real SAP Basis error formats — not sampled from a production system.
- The corpus covers 16 runbooks across 8 incident categories; any incident outside those categories, or any incident this corpus simply does not describe, has no chance of a correct answer regardless of retrieval quality.
- Single-author bias: runbook content, the eval-case labels, and the difficulty tiers were all written by one person, who may unconsciously write eval queries that resemble their own runbook phrasing more than a real incident would.
- The `[A-Za-z0-9_/]+` BM25 tokenizer cannot segment Thai text (no inter-word spaces), so Thai queries contribute **zero** BM25 tokens — the Thai slice in the headline table is carried entirely by the dense/embedding side (research.md R-05).

