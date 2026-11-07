# Phase 1 Data Model: Runbook Corpus, Labelled Eval Set, Measured Retrieval

**Feature**: `001-runbook-retrieval-eval` | **Date**: 2026-11-07

Maps the 11 entities from [spec.md](./spec.md) onto concrete Pydantic v2 models and on-disk shapes.
Every validation rule cites the requirement it implements. Models live in `app/schemas.py` unless
noted; eval-only models live in `eval/schema.py`.

---

## Enumerations

```python
Category = Literal[
    "memory_dump", "timeout", "job_failure", "lock_issue",
    "update_error", "transport_error", "user_auth", "rfc_error",
]
# "out_of_scope" is a valid eval-case label but never a runbook category.
EvalCategory = Literal[*Category.__args__, "out_of_scope"]

SectionName   = Literal["Symptoms", "Cause", "Check", "Fix", "Escalate", "References"]
EscalateTo    = Literal["basis", "developer", "security", "dba", "network", "sap_support"]
ChunkStrategy = Literal["fixed", "section"]
RetrievalMode = Literal["dense", "bm25", "hybrid"]
Split         = Literal["dev", "test"]
Difficulty    = Literal["easy", "medium", "hard"]
LogFormat     = Literal["st22_header", "sm37_joblog", "sm21_syslog", "stms_log",
                        "sm59_test", "user_email", "chat_thai", "hana_alert", "other"]
FailureType   = Literal["retrieval_miss", "gate_false_refusal", "gate_missed_oos", "partial_recall"]
```

`SECTION_ORDER = ("Symptoms", "Cause", "Check", "Fix", "Escalate", "References")` — the required
order, asserted by the parser (FR-003).

---

## 1. Runbook

One incident playbook. Source of truth for retrieval, citations, and eval labels.

| Field | Type | Rules |
|---|---|---|
| `doc_id` | `str` | `^[a-z][a-z0-9_]{2,39}$`; unique across corpus; equals the filename stem (FR-002) |
| `category` | `Category` | exactly one (FR-002) |
| `title` | `str` | 5–120 chars (FR-002) |
| `tcodes` | `list[str]` | 1–8 entries, ordered as they should be opened; every entry a key of `tcodes.json` (FR-004, FR-006) |
| `escalate_to` | `EscalateTo` | required (FR-002) |
| `references` | `list[HttpUrl]` | `min_length=1` (FR-002, FR-005, X) |
| `sections` | `dict[SectionName, str]` | exactly the 6 names, in `SECTION_ORDER`, each body 20–1500 chars (FR-003) |
| `source_path` | `Path` | populated by the parser, excluded from serialisation |

**Relationships**: owns 6 `RunbookSection`s; referenced by `EvalCase.gold_docs` /
`acceptable_docs`; its `tcodes` must all exist in the T-code allow-list.

**Corpus-level invariants** (`runbooks.load_corpus()` raises `CorpusError` naming the file and value):

- exactly 16 runbooks, 2 per category (FR-001)
- `doc_id` unique (FR-002)
- every T-code named in front-matter **or** matched by the T-code regex inside a `## Check` body is a
  key of `tcodes.json` (FR-007, SC-006)
- `## References` body contains at least one URL matching the front-matter `references` list (X)

---

## 2. RunbookSection

Not a separate file — a derived view, and the citable unit.

| Field | Type | Rules |
|---|---|---|
| `doc_id` | `str` | parent runbook |
| `section` | `SectionName` | one of the six |
| `text` | `str` | the section body |
| `address` | `str` | computed `f"{doc_id}#{section.lower()}"` (FR-010) |

**Why it exists**: `address` is the citation format Feature 2 will emit and verify. Fixing it here
means the eval set, search output, and later triage output all speak the same identifier.

---

## 3. TcodeEntry — the allow-list

On disk `data/tcodes.json` is a flat object `{"<CODE>": "<one-line description>"}`.

| Field | Type | Rules |
|---|---|---|
| `code` | `str` | `^[A-Z][A-Z0-9_/]{1,19}$` (FR-006) |
| `description` | `str` | 5–120 chars, single line (FR-006) |

**Role**: bounds what the corpus may name (FR-007) and supplies half the rare-token test in R-03.
Loaded once into `dict[str, str]`; also exposed as `frozenset` of codes for the gate.

---

## 4. Chunk — a searchable unit

One line of `data/index/chunks.jsonl`.

| Field | Type | Rules |
|---|---|---|
| `chunk_id` | `str` | section strategy: `"{doc_id}#{section_lower}"`; fixed strategy: `"{doc_id}#f{ordinal}"` — unique within the index (FR-010) |
| `doc_id` | `str` | must resolve to a corpus runbook (FR-010, SC-005) |
| `category` | `Category` | copied from the runbook, for later metadata filtering |
| `section` | `SectionName \| None` | `None` under `fixed` chunking when the window spans sections |
| `title` | `str` | copied from the runbook |
| `text` | `str` | embedded/indexed text, including the context prefix below |
| `row` | `int` | index into `embeddings.npy`; `chunks.jsonl` line *n* ↔ matrix row *n* |

**Context prefix** (section strategy only): each chunk's `text` is prefixed
`"[{title}] [{category}] {section}: "` so an isolated chunk still carries its subject. This is part of
the embedded text and therefore part of what E1 measures.

**Strategies** (`app/retrieval/chunk.py`, pure functions):

- `chunk_fixed(text, size=800, overlap=150)` — the naive default, matching the course reference app.
  Produces the R-Dense-naive baseline.
- `chunk_by_section(runbook)` — one chunk per `## ` section; 6 chunks per runbook, ≈96 total.

**Invariant**: `len(chunks) == embeddings.shape[0]`, asserted on load. Row/line misalignment is the
one corruption mode that produces plausible-looking wrong answers.

---

## 5. IndexManifest

`data/index/manifest.json` — the index's identity (R-06).

| Field | Type | Purpose |
|---|---|---|
| `corpus_sha` | `str` | SHA-256 over sorted `runbooks/*.md` + `tcodes.json` bytes; staleness check (FR-020) |
| `chunk_strategy` | `ChunkStrategy` | which strategy produced this index |
| `embed_model` | `str \| None` | `"bge-m3"`; `None` for a `--no-embed` build |
| `embed_dim` | `int \| None` | `1024`, asserted against the matrix; `None` for `--no-embed` |
| `n_runbooks` | `int` | build report (FR-012) |
| `n_chunks` | `int` | build report (FR-012) |
| `n_vectors` | `int` | `n_chunks`, or `0` for a `--no-embed` build |
| `built_at` | `str` | ISO-8601 UTC; informational only, never compared |
| `git_commit` | `str \| None` | short hash, or `None` outside a repo |

A `--no-embed` index (`n_vectors == 0`) is valid for `bm25` mode only — it is what makes the first
recall@3 measurable with no network (SC-012, R-12 step 6). `dense`/`hybrid` against it raises rather
than downgrading silently, so no results file can mislabel which mode produced it.

`store.load()` recomputes `corpus_sha` and raises `StaleIndexError` on mismatch, naming
`python -m app.cli ingest` as the fix.

---

## 6. Hit — one search result

Returned by `search()`; never persisted. Full contract in
[contracts/search.md](./contracts/search.md).

| Field | Type | Rules |
|---|---|---|
| `chunk_id` | `str` | resolvable address (FR-014, SC-005) |
| `doc_id` | `str` | distinct across a single result list (FR-015, R-07) |
| `section` | `SectionName \| None` | section name (FR-014) |
| `text` | `str` | the section text returned to the caller (FR-014) |
| `dense_score` | `float \| None` | cosine in `[-1, 1]`; `None` in `bm25` mode |
| `bm25_score` | `float \| None` | raw BM25; `None` in `dense` mode |
| `fused_score` | `float \| None` | RRF score; `hybrid` mode only |
| `rank` | `int` | 1-based position in the returned list (FR-014) |

**Score reporting rule**: the CLI and results files print whichever score the active mode actually
ranked by, labelled with its name — never an RRF score presented as if it were a cosine.

---

## 7. EvalCase

One line of `eval/cases_dev.jsonl` / `eval/cases_test.jsonl` (`eval/schema.py`).

| Field | Type | Rules |
|---|---|---|
| `id` | `str` | `^[dt]\d{2}$` (`d01`…`d10`, `t01`…`t30`); unique (FR-026) |
| `split` | `Split` | must match the file it is loaded from (FR-022) |
| `format` | `LogFormat` | the log's shape (FR-026) |
| `difficulty` | `Difficulty` | tier (FR-026) |
| `log` | `str` | 10–4000 chars, synthetic (FR-026, FR-028) |
| `gold_category` | `EvalCategory` | expected category (FR-026) |
| `gold_docs` | `list[str]` | expected runbooks; **empty iff** `gold_category == "out_of_scope"` (FR-026, FR-027) |
| `acceptable_docs` | `list[str]` | alternatives; no recall credit, no failure record (FR-034) |
| `gold_tcodes` | `list[str]` | the 2–3 that must appear; every entry in the allow-list (FR-026) |
| `synthetic` | `bool` | default `True`, must be `True` (FR-028) |
| `notes` | `str` | free text, may be Thai; why the case is labelled this way |

**Per-case validators**: `gold_docs` and `acceptable_docs` disjoint; every id in either resolves to a
corpus runbook (FR-030); out-of-scope cases have empty `gold_docs`, `acceptable_docs`, and
`gold_tcodes` (FR-027); in-scope cases have non-empty `gold_docs`.

---

## 8. EvalSet — split-level invariants

`eval/schema.py: load_split(split) -> EvalSet`. These are the properties SC-001/SC-002/SC-003 assert,
and `tests/test_eval_cases.py` runs them as a test so the set cannot silently drift.

**Dev split** (10 cases, tuning only):

- 8 in-scope, exactly 1 per category; 2 out-of-scope (spec Assumptions)

**Test split** (30 cases, reporting only):

- 24 in-scope with exactly 3 per category, one each `easy` / `medium` / `hard` (FR-023)
- 4 out-of-scope (FR-023)
- 2 mixed — in-scope with `len(gold_docs) >= 2` (FR-023)
- exactly 3 cases with `format == "chat_thai"`, all `difficulty == "hard"` (FR-024)
- every one of the 16 `doc_id`s appears in some test case's `gold_docs` (FR-025, SC-002)

**Cross-split**:

- no `log` appears in both splits, and no pair of logs is identical after case-folding and
  whitespace collapse (guards the eval-plan rule against near-duplicate dev/test cases)
- **no case `log` shares a contiguous 8-word span with any runbook section text** (FR-029, SC-003) —
  computed over lower-cased, punctuation-stripped word shingles across all cases × all sections

**Derived populations** (R-08): `in_scope` = non-empty `gold_docs` (26 test / 8 dev); `out_of_scope` =
`gold_category == "out_of_scope"` (4 test / 2 dev). Mixed cases are in-scope *and* reported as a slice.

---

## 9. RunResult — one configuration over one split

`eval/results/{experiment}_{config_slug}.json`, written by `run_retrieval.py` (R-11).

```text
RunConfig:  experiment, name, split, mode, chunk_strategy, k, min_score,
            embed_model, corpus_sha, git_commit
CaseResult: case_id, difficulty, format, retrieved[ {doc_id, chunk_id, score, rank} ],
            gated_out: bool, recall_at_k_pre, recall_at_k_post, rr_pre, rr_post,
            correct_gate: bool | None
Aggregate:  n_in_scope, n_out_of_scope,
            recall_at_3_pre, mrr_pre,          # ranking quality      (R-01)
            recall_at_3_post, mrr_post,        # delivered quality    (R-01)
            oos_gate_accuracy, false_refusal_rate,
            by_difficulty: { easy|medium|hard|thai|mixed|oos -> same metric block }
```

**Invariants**: `config` is never written by hand; `corpus_sha` and `git_commit` are copied from the
loaded manifest, not recomputed (FR-035); a run whose manifest `chunk_strategy` disagrees with its
`RunConfig.chunk_strategy` aborts rather than mislabelling the result.

---

## 10. Comparison

Not a stored entity — a view `run_all.py` builds over `RunResult` files to emit `results.md` (FR-037).

| Field | Meaning |
|---|---|
| `experiment` | `E1` chunking, `E2` mode, `E3` min_score sweep |
| `varied_variable` | the single field differing across rows, named in the table header |
| `baseline_name` | `R-BM25` or `R-Dense-naive` (FR-038) |
| `rows` | `RunConfig` + `Aggregate` per configuration, all on the same split |
| `delta` | per-metric difference against the row's baseline |
| `verdict` | generated sentence, including when the combined mode loses (FR-044, SC-014) |

**Invariant**: all rows in one comparison share `split` and `corpus_sha`; `run_all.py` refuses to
emit a table whose rows disagree on either, since the comparison would be meaningless.

---

## 11. FailureRecord

One line of `eval/results/failures.jsonl`; the file is truncated at the start of `run_all.py` and
always created, even when empty (FR-042, FR-043).

| Field | Type | Notes |
|---|---|---|
| `case_id` | `str` | |
| `config_name` | `str` | which run produced it |
| `expected_category` | `EvalCategory` | |
| `expected_docs` | `list[str]` | `gold_docs` |
| `acceptable_docs` | `list[str]` | shown for context; their presence is not the failure |
| `retrieved` | `list[{doc_id, section, score, rank}]` | in returned order (FR-042) |
| `failure_type` | `FailureType` | miss / false refusal / missed out-of-scope / partial recall |
| `note` | `str` | the case's `notes`, carried through for the report |

**Rule**: a case retrieving only `acceptable_docs` is recorded as `retrieval_miss` only when no
`gold_doc` was found — matching an acceptable alternative is never itself a failure (FR-034).

---

## Entity relationships

```text
TcodeEntry (allow-list) ──bounds── Runbook.tcodes
                                      │
Runbook ──owns 6──> RunbookSection ──address "doc_id#section"
   │                      │
   │ chunked by strategy  ▼
   └──────────────> Chunk ──row──> embeddings.npy
                      │              ▲
                      └── indexed by store ── IndexManifest.corpus_sha
                                      │
EvalCase.gold_docs ──references──> Runbook.doc_id
   │
   └── scored against ──> Hit ──aggregated──> RunResult ──compared──> Comparison
                                      │
                                      └──failing cases──> FailureRecord
```
