# Contract: File Formats

**Feature**: `001-runbook-retrieval-eval`

Every on-disk shape this feature reads or writes. Field-level rules and their requirement references
live in [data-model.md](../data-model.md); this document fixes the literal file layout so the corpus,
the eval set, and the results are mutually parseable.

Committed: `data/runbooks/*.md`, `data/tcodes.json`, `eval/cases_*.jsonl`, `eval/results/*`.
Generated: `data/index/*`. Git-ignored: `data/cache/`, `.env`.

---

## 1. `data/runbooks/<doc_id>.md` — committed, 16 files

YAML front-matter, then exactly six `## ` sections in fixed order. The filename stem **is** the
`doc_id`. The chunker splits on `## `, so these headings are a parsing contract, not formatting.

```markdown
---
doc_id: mem_tsv_tnew_page_alloc
category: memory_dump
title: TSV_TNEW_PAGE_ALLOC_FAILED — internal table cannot grow
tcodes: [ST22, ST02, RZ11, SM37, SM21]
escalate_to: developer
references:
  - https://help.sap.com/docs/...
  - https://community.sap.com/...
---

## Symptoms
Dump text the user actually sees, including the verbatim runtime error name so keyword
search can match it. 40–150 words.

## Cause
Most frequent causes first. 40–150 words.

## Check
1. ST22 — Error analysis: requested vs already-used size; Chosen variables; program and job.
2. ST02 — extended memory and heap usage, including historical peaks.
3. RZ11 — ztta/roll_extension, abap/heap_area_dia, abap/heap_area_total.

## Fix
What to do per cause, and explicitly what not to do first.

## Escalate
When to hand off and to whom, with what attached.

## References
- SAP Help — ABAP Dump Analysis — https://help.sap.com/docs/...
- SAP Community — TSV_TNEW_PAGE_ALLOC_FAILED — https://community.sap.com/...
```

**Rules**

- `tcodes` is ordered as the T-codes should be opened (FR-004); every entry is a key of `tcodes.json`.
- `references` has at least one URL; the `## References` body restates them with titles (FR-002, X).
- `## Check` is a numbered list, each item `<T-CODE> — <what to look for>`.
- Content is the author's own words summarising public SAP documentation. No SAP Notes text, no long
  SAP documentation passages (FR-005, Constitution X).
- `ingest` fails with exit 2 on a missing/extra/misordered section, a T-code outside the allow-list,
  or zero references — naming the file and the offending value (FR-007).
- Exactly 2 files per category, 16 total (FR-001).

---

## 2. `data/tcodes.json` — committed

Flat object, sorted by key, one line per entry.

```json
{
  "AL08": "List of all logged-on users across instances",
  "SM12": "Lock entries — display and delete enqueue locks",
  "SM37": "Background job overview — status, job log, step details",
  "ST22": "ABAP dump analysis — short dumps and runtime errors"
}
```

Keys match `^[A-Z][A-Z0-9_/]{1,19}$`; values are single-line, 5–120 characters (FR-006). This file is
the allow-list that bounds the corpus (FR-007) and supplies half the rare-token rule
([search.md](./search.md#gate-semantics-fr-018-r-02-r-03)).

---

## 3. `data/index/chunks.jsonl` — generated

One JSON object per line. **Line *n* corresponds to row *n* of `embeddings.npy`** — the alignment
invariant asserted on load.

```json
{"chunk_id":"mem_tsv_tnew_page_alloc#cause","doc_id":"mem_tsv_tnew_page_alloc","category":"memory_dump","section":"Cause","title":"TSV_TNEW_PAGE_ALLOC_FAILED — internal table cannot grow","text":"[TSV_TNEW_PAGE_ALLOC_FAILED — internal table cannot grow] [memory_dump] Cause: An internal table needed more memory than the work process could reserve …","row":1}
```

Under `fixed` chunking `section` is `null` when a window spans sections, and `chunk_id` is
`"{doc_id}#f{ordinal}"`. The `text` field includes the context prefix and is exactly what was
embedded and BM25-indexed — so E1 measures the prefix too.

---

## 4. `data/index/embeddings.npy` — generated

`numpy` array, shape `(n_chunks, 1024)`, dtype `float32`, **L2-normalised row-wise** so a dot product
is the cosine. Row order matches `chunks.jsonl` line order. `store.load()` asserts
`shape[0] == len(chunks)` and `shape[1] == manifest.embed_dim`.

Absent under a `--no-embed` build; `bm25` mode never reads it.

---

## 5. `data/index/manifest.json` — generated

```json
{
  "corpus_sha": "3f9a1c2e8b47…",
  "chunk_strategy": "section",
  "embed_model": "bge-m3",
  "embed_dim": 1024,
  "n_runbooks": 16,
  "n_chunks": 96,
  "n_vectors": 96,
  "built_at": "2026-11-07T09:14:22Z",
  "git_commit": "37eb1df"
}
```

Under a `--no-embed` build: `embed_model` and `embed_dim` are `null`, `n_vectors` is `0`, and
`embeddings.npy` is absent. `store.load()` accepts such an index for `bm25` mode and raises for
`dense`/`hybrid` with a message naming the re-ingest fix (never a silent downgrade to keyword-only).

`corpus_sha` is SHA-256 over the concatenated bytes of `data/runbooks/*.md` and `data/tcodes.json` in
sorted filename order. `store.load()` recomputes it and raises `StaleIndexError` on mismatch (FR-020,
R-06). `built_at` is informational and never compared.

---

## 6. `data/cache/<sha256>.json` — generated, git-ignored

One file per embedded text, key `sha256(f"{model}|{text}")`:

```json
{"model":"bge-m3","dim":1024,"vector":[0.0131,-0.0422, "…1024 floats"]}
```

Content-addressed, so a cache hit is byte-identical to the original response — the mechanism behind
"two runs give identical numbers" (FR-036, SC-004, R-09). Not committed: binary-ish bulk in history
for a regenerable artifact.

---

## 7. `eval/cases_dev.jsonl` (10) / `eval/cases_test.jsonl` (30) — committed

One case per line. `\n` inside `log` is JSON-escaped, so multi-line dumps stay on one line.

```json
{"id":"t07","split":"test","format":"sm37_joblog","difficulty":"hard","log":"Job log overview for job ZSD_BILLING_DAILY / 02150300\n02:15:03 Job started\n02:15:04 User SD_BATCH is locked. Please notify the person responsible\n02:15:04 Job cancelled after system exception ERROR_MESSAGE","gold_category":"job_failure","gold_docs":["job_cancelled"],"acceptable_docs":["user_locked"],"gold_tcodes":["SM37","SU01"],"synthetic":true,"notes":"step user locked is the root cause — needs two searches"}
```

```json
{"id":"t28","split":"test","format":"hana_alert","difficulty":"medium","log":"HANA alert 2: Log volume /hana/log/HDB is 98% full. Log backups failing since 04:00.","gold_category":"out_of_scope","gold_docs":[],"acceptable_docs":[],"gold_tcodes":[],"synthetic":true,"notes":"no HANA runbook — must be refused"}
```

Split-level invariants (counts, per-category and per-difficulty distribution, 3 Thai hard cases,
every runbook covered, no cross-split duplicates, no 8-word span shared with runbook text) are listed
in [data-model.md § 8](../data-model.md#8-evalset--split-level-invariants) and enforced by
`tests/test_eval_cases.py`.

---

## 8. `eval/results/{experiment}_{config_slug}.json` — committed

One file per (experiment, configuration, split); never overwritten by a different configuration
(R-11). Slug example: `E2_hybrid-section-k3-ms045_test`.

```json
{
  "config": {
    "experiment": "E2", "name": "hybrid + section", "split": "test",
    "mode": "hybrid", "chunk_strategy": "section", "k": 3, "min_score": 0.40,
    "embed_model": "bge-m3", "corpus_sha": "3f9a1c2e8b47…", "git_commit": "37eb1df"
  },
  "aggregate": {
    "n_in_scope": 26, "n_out_of_scope": 4,
    "recall_at_3_pre": 0.0, "mrr_pre": 0.0,
    "recall_at_3_post": 0.0, "mrr_post": 0.0,
    "oos_gate_accuracy": 0.0, "false_refusal_rate": 0.0,
    "by_difficulty": {"easy": {}, "medium": {}, "hard": {}, "thai": {}, "mixed": {}, "oos": {}}
  },
  "cases": [
    {"case_id": "t07", "difficulty": "hard", "format": "sm37_joblog",
     "retrieved": [{"doc_id": "job_cancelled", "chunk_id": "job_cancelled#symptoms", "score": 0.62, "rank": 1}],
     "gated_out": false,
     "recall_at_k_pre": 1.0, "recall_at_k_post": 1.0, "rr_pre": 1.0, "rr_post": 1.0,
     "correct_gate": null}
  ]
}
```

Zeros above are placeholders showing shape — real files contain measured values only. `config` is
machine-written; `corpus_sha` and `git_commit` are copied from the loaded manifest, never recomputed
(FR-035). Both pre- and post-gate aggregates are always present (R-01).

---

## 9. `eval/results/failures.jsonl` — committed

Truncated at the start of each `run_all.py`, then appended; **always created, even when empty**
(FR-043).

```json
{"case_id":"t29","config_name":"hybrid + section","expected_category":"lock_issue","expected_docs":["lock_old_entries"],"acceptable_docs":[],"retrieved":[{"doc_id":"update_terminated","section":"Symptoms","score":0.51,"rank":1},{"doc_id":"lock_table_overflow","section":"Cause","score":0.47,"rank":2}],"failure_type":"retrieval_miss","note":"mixed log — two problems in one text"}
```

---

## 10. `eval/results/results.md` — committed, generated

Regenerated wholesale by `run_all.py`; **never hand-edited** (Constitution II). Required contents:

1. **Run header** — `corpus_sha`, git commit, embed model, date, and which splits were used.
2. **E1 chunking** — `fixed-800/150` vs `section`, dense, k=3, **pre-gate** metrics, variable named.
3. **E2 retrieval mode** — `bm25` / `dense` / `hybrid` on the winning chunking, **pre-gate**, with
   R-BM25 and R-Dense-naive marked as the named baselines (FR-038).
4. **E3 `min_score` sweep** — dev only, 0.30→0.60 step 0.05, post-gate in-scope recall against
   out-of-scope rejection; the chosen value and the run it came from.
5. **Headline test table** — final configuration, **post-gate**, with out-of-scope gate accuracy and
   false-refusal rate; the BM25 row flagged as gated by the token rule alone (R-02).
6. **Per-difficulty slices** — easy / medium / hard / Thai / mixed / out-of-scope.
7. **Verdict sentence** — stated plainly, including when the combined mode does not win (FR-044,
   SC-014).
8. **Limitations** — synthetic logs, 16-runbook corpus, single-author bias, Thai contributing nothing
   to BM25 (R-05), and any case the author knows is mislabelled.

Every table header states whether its numbers are pre-gate or post-gate (R-01).

---

## 11. `.env.example` — committed; `.env` — git-ignored

Copied verbatim from `docs/prepare/templates/env.example` so the project-wide example file does not
have to change between features:

```bash
# Copy to .env (never commit .env). OpenAI() reads OPENAI_BASE_URL / OPENAI_API_KEY automatically.
OPENAI_BASE_URL=https://llm.nat-d.uk/v1
OPENAI_API_KEY=sk-replace-me

CHAT_MODEL=gemma-4-E4B-it
EMBED_MODEL=bge-m3

# Retrieval: RETRIEVAL_MODE = dense | bm25 | hybrid ; CHUNK_STRATEGY = fixed | section
RETRIEVAL_MODE=hybrid
CHUNK_STRATEGY=section
TOP_K=3
# MIN_SCORE is a placeholder - tune it on eval/cases_dev.jsonl (experiment E3)
MIN_SCORE=0.40

# Agent
MAX_STEPS=5
```

Read in exactly one module, `app/config.py` (Constitution V). This feature consumes seven of the nine
variables — `CHAT_MODEL` and `MAX_STEPS` belong to Feature 2's agent and are present only so the
example file is stable across features; `app/config.py` does not expose them yet.

`MIN_SCORE` ships as a placeholder precisely because its value must come from a measurement, not a
guess. `0.40` matches the reference app's value for its own corpus (`docs/prepare/03_tech_stack.md`
§ 3) and carries no claim about ours.
