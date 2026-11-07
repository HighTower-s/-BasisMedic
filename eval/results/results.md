# BasisMedic — Retrieval Evaluation Report

- corpus_sha: `49b07d941e2b3e4b76a3fa0c7c94a434e6e5d5709952d25cb914acdf65252018`
- git commit: `2d7000f`
- embed model: `bge-m3`
- generated: 2026-11-07T15:30:43Z
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
