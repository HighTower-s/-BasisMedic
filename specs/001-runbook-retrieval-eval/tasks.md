---

description: "Task list for Feature 001 — runbook corpus, labelled eval set, measured retrieval"
---

# Tasks: Runbook Corpus, Labelled Eval Set, and Measured Retrieval

**Input**: Design documents from `/specs/001-runbook-retrieval-eval/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Test tasks **are** included. Constitution VIII mandates unit tests for every deterministic
part with the gateway mocked, and plan.md § Constitution Check commits to them — so they are a
requirement here, not an option. Answer quality is measured by the eval harness, never asserted in a
unit test.

**Organization**: Tasks are grouped by user story. See the ordering note below for why the corpus and
the evaluation set sit in Foundational rather than inside User Story 1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1–US6)
- Exact file paths are given in every task

## Path Conventions

Single Python project at the repository root, per [plan.md § Structure Decision](./plan.md#structure-decision):
`app/` (config, llm, schemas, normalize, cli, retrieval/), `eval/`, `data/`, `tests/`.

---

## ⚠️ Ordering note: why the eval set is Foundational

Spec user stories put the labelled eval set inside US2. **Constitution Principle I
(NON-NEGOTIABLE)** requires it to be written and committed *before* any retrieval code exists, and
FR-021 restates that. Those two cannot both be honoured if US2 runs after US1 (the index).

Resolution: the corpus and the evaluation set move into **Phase 2 Foundational**. This is defensible
on the template's own terms — neither is optional for any of the six stories, so both are genuinely
"blocking prerequisites for all user stories". Consequences, stated rather than hidden:

- **US1's phase covers acceptance scenarios 3 and 4** (clean rebuild, resolvable addresses).
  Scenarios 1 and 2 (corpus validation, T-code allow-list enforcement) are satisfied by T019 + T021
  in Foundational.
- **US2's phase covers the harness and the first measured numbers**, not the case files themselves.
- T036 is an explicit gate that `git log` shows the eval set committed before `chunk.py`,
  `store.py`, and `search.py` — the only real evidence for Principle I.

Within the stories, order follows [research.md R-12](./research.md#r-12--task-ordering-is-the-mechanism-that-enforces-evaluation-first):
BM25 and the first offline recall@3 (US2) land **before** any embedding code (US3). That is
deliberate — it de-risks the gateway being unavailable on demo day and is what makes SC-012
satisfiable.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton, dependency management, configuration seam, test harness.

- [X] T001 Create the package skeleton with `__init__.py` in `app/`, `app/retrieval/`, `eval/`, and directories `data/runbooks/`, `tests/` per plan.md § Source Code
- [X] T002 Create `pyproject.toml` for Python 3.12 with dependencies `openai>=1.40`, `numpy>=1.26`, `rank-bm25>=0.2.2`, `pydantic>=2.7`, dev `pytest>=8.0`; no orchestration framework and no vector DB (Constitution V); generate `uv.lock` via `uv sync`
- [X] T003 [P] Create `.env.example` by copying `docs/prepare/templates/env.example` verbatim (9 variables): `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `CHAT_MODEL`, `EMBED_MODEL`, `RETRIEVAL_MODE=hybrid`, `CHUNK_STRATEGY=section`, `TOP_K=3`, `MIN_SCORE=0.40` (placeholder — real value comes from the E3 sweep), `MAX_STEPS=5`. `CHAT_MODEL` and `MAX_STEPS` are unused in this feature but belong in the project-wide example so Feature 2 does not have to edit it
- [X] T004 [P] Create `.gitignore` by copying `docs/prepare/templates/gitignore.txt`: `.env`, `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `data/cache/`. **Decide `data/index/` explicitly** — the template leaves it open; committing it makes `eval` reproducible without re-embedding, which the risk register in `docs/prepare/10_timeline_and_checklist.md` § 7 recommends against the gateway being down near the deadline
- [X] T005 Implement `app/config.py` as the **only** reader of environment variables (Constitution V): typed accessors for the seven variables this feature uses (all but `CHAT_MODEL` and `MAX_STEPS`) with the defaults above, plus `ConfigError` raised on missing/malformed values; never log or echo `OPENAI_API_KEY`
- [X] T006 [P] Configure pytest in `pyproject.toml` and create `tests/conftest.py` with a 3-runbook fake-corpus fixture and a `mock_embed` fixture that patches `app.llm.embed` — every test must run with no network

**Checkpoint**: `uv sync` succeeds, `uv run pytest` collects zero tests without error.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared schemas, the runbook corpus, the T-code allow-list, the labelled evaluation set,
and the metric functions. Constitution I requires the eval set here.

**⚠️ CRITICAL**: No user story work may begin until this phase is complete.

### Shared schemas

- [X] T007 Define the enumerations in `app/schemas.py` verbatim from data-model.md § Enumerations: `Category` (8 values, `out_of_scope` excluded), `EvalCategory` (9 values), `SectionName`, `EscalateTo`, `ChunkStrategy`, `RetrievalMode`, `Split`, `Difficulty`, `LogFormat`, `FailureType`, and `SECTION_ORDER = ("Symptoms","Cause","Check","Fix","Escalate","References")`
- [X] T008 Define the `Runbook` Pydantic v2 model in `app/schemas.py` with the constraints quoted from data-model.md § 1: `doc_id` matching `^[a-z][a-z0-9_]{2,39}$`, `title` 5–120 chars, `tcodes` 1–8 entries, `references` `min_length=1` of `HttpUrl`, `sections` exactly the 6 `SectionName` keys in `SECTION_ORDER` with each body 20–1500 chars, `source_path` excluded from serialisation
- [X] T009 [P] Define `Chunk` (`chunk_id`, `doc_id`, `category`, `section` nullable, `title`, `text`), `Hit` (`chunk_id`, `doc_id`, `section`, `text`, `dense_score`/`bm25_score`/`fused_score` all nullable, `rank` 1-based), and `IndexManifest` (`embed_model`/`embed_dim` nullable, `n_vectors`) in `app/schemas.py` per data-model.md §§ 4, 5, 6. **Ponytail deviation**: no separate `TcodeEntry` model — `tcodes.json` loads as a plain `dict[str, str]` with the key/description rules asserted once in `load_tcodes()` (app/retrieval/runbooks.py); a model would duplicate that check for no caller. Also no `Chunk.row` — a chunk's row is its position in the list `ingest.py` builds, not a second stored fact that could drift from it

### T-code allow-list and corpus parser

- [X] T010 Create `data/tcodes.json` from `docs/prepare/templates/tcodes.json` (52 entries, already in the required flat key-description shape); verify it covers every T-code the 16 runbooks reference per `docs/prepare/07_short_dump_and_incidents.md` — including **ST12, ST01, ST04, DBACOCKPIT**, which runbooks R04 and R14 need — then sort by key (contracts/file-formats.md § 2)
- [X] T011 Implement `app/retrieval/runbooks.py`: parse YAML front-matter and split body on `## ` into the six sections, returning `Runbook` objects; raise `CorpusError` naming the file and the offending value on a missing, extra, or misordered section, on zero references, or on any T-code absent from `data/tcodes.json` (FR-007)
- [X] T012 Add corpus-level invariants to `app/retrieval/runbooks.py:load_corpus()`: exactly 16 runbooks, exactly 2 per category across the 8 categories, unique `doc_id`s, and every T-code matched inside a `## Check` body also allow-listed (FR-001, FR-002, SC-006)
- [X] T013 Implement `corpus_sha()` in `app/retrieval/runbooks.py`: SHA-256 over the concatenated bytes of `data/runbooks/*.md` and `data/tcodes.json` in sorted filename order (research.md R-06)

### Runbook content — 16 files, own words, with references (Constitution X)

Source material: `docs/prepare/07_short_dump_and_incidents.md`. Each file follows
`docs/prepare/templates/runbook_TEMPLATE.md` and contracts/file-formats.md § 1: six sections,
each body 40–150 words, verbatim runtime-error names in `## Symptoms` to help keyword search, `## Check`
as a numbered `<T-CODE> — <what to look for>` list, at least one reference URL. **No verbatim SAP
documentation or SAP Notes text.**

- [X] T014 [P] Write `data/runbooks/mem_tsv_tnew_page_alloc.md` and `data/runbooks/mem_system_no_roll.md` (category `memory_dump`)
- [X] T015 [P] Write `data/runbooks/timeout_dialog.md` and `data/runbooks/timeout_long_running_wp.md` (category `timeout`)
- [X] T016 [P] Write `data/runbooks/job_cancelled.md` and `data/runbooks/job_stuck_ready_released.md` (category `job_failure`)
- [X] T017 [P] Write `data/runbooks/lock_old_entries.md` and `data/runbooks/lock_table_overflow.md` (category `lock_issue`)
- [X] T018 [P] Write `data/runbooks/update_terminated.md` and `data/runbooks/update_deactivated.md` (category `update_error`)
- [X] T019 [P] Write `data/runbooks/transport_rc8.md` and `data/runbooks/transport_rc12_or_stuck.md` (category `transport_error`)
- [X] T020 [P] Write `data/runbooks/user_locked.md` and `data/runbooks/auth_missing.md` (category `user_auth`)
- [X] T021 [P] Write `data/runbooks/rfc_connection_failed.md` and `data/runbooks/rfc_trfc_queue.md` (category `rfc_error`)
- [X] T022 Write `tests/test_runbooks.py` covering US1 acceptance scenarios 1–2: all corpus invariants from T012, and that adding an unlisted T-code fails naming file and code (FR-007, SC-006)

### Labelled evaluation set — BEFORE any retrieval module exists (Constitution I, FR-021)

- [X] T023 Implement the `EvalCase` model in `eval/schema.py` with the constraints quoted from data-model.md § 7: `id` matching `^[dt]\d{2}$`, `log` 10–4000 chars, `synthetic` defaulting to `True` and required `True`, `gold_docs` empty **iff** `gold_category == "out_of_scope"`, `gold_docs`/`acceptable_docs` disjoint, every referenced `doc_id` resolving in the corpus, every `gold_tcode` in the allow-list (FR-026, FR-027, FR-030)
- [X] T024 Author `eval/cases_dev.jsonl` — exactly 10 cases: 8 in-scope, one per category, plus 2 out-of-scope. Logs synthetic and modelled on real formats; `docs/prepare/templates/eval_cases.example.jsonl` holds 8 usable drafts (add the missing `user_auth` case and a second out-of-scope case)
- [X] T025 Author `eval/cases_test.jsonl` — exactly 30 cases: 24 in-scope as 3 per category (one `easy` with an exact error code, one `medium` in another log format, one `hard` with no exact code), 4 out-of-scope, 2 mixed with `len(gold_docs) >= 2`; exactly 3 `hard` cases with `format == "chat_thai"`; every one of the 16 runbooks the `gold_docs` of at least one case (FR-023, FR-024, FR-025)
- [X] T026 Implement `load_split(split)` and the split-level validators in `eval/schema.py` per data-model.md § 8: per-split counts, per-category and per-difficulty distribution, Thai-case count, full runbook coverage, no cross-split duplicate logs, and the derived `in_scope` / `out_of_scope` populations (26/4 test, 8/2 dev — research.md R-08)
- [X] T027 Implement the copied-phrasing check in `eval/schema.py`: no case `log` shares a contiguous 8-word span with any runbook section text, over lower-cased punctuation-stripped word shingles across all cases × all sections (FR-029, SC-003). **Refinement found during implementation**: the check excludes each runbook's `Symptoms` section — `09_eval_plan.md` and `runbook_TEMPLATE.md` both require Symptoms to quote the literal SAP error text, which an "easy" case is defined by also quoting; flagging that would make the easy tier unwritable. Cause/Check/Fix/Escalate/References are still checked, which is what FR-029 actually targets (copied analysis prose, not a shared official error string)
- [X] T028 Write `tests/test_eval_cases.py` asserting every invariant from T023, T026, and T027 — this is the mechanical form of SC-001, SC-002, and SC-003

### Metric functions

- [X] T029 Implement pure functions in `eval/metrics.py`: `recall_at_k(ranked_docs, relevant_docs, k)`, `mrr(ranked_docs, relevant_docs)`, `gate_accuracy(results)`, `false_refusal_rate(results)` — all collapsing retrieved chunks to `doc_id` before ranking, with `acceptable_docs` earning no credit (FR-032, FR-033, FR-034)
- [X] T030 [P] Write `tests/test_metrics.py` with hand-computed fixtures: gold at rank 1/2/3/absent, two-gold partial recall for mixed cases, empty ranked list, and an acceptable-only result scoring zero recall without being a failure

**Checkpoint**: `uv run pytest -q` passes offline. The corpus and the 40-case eval set are committed
and valid. **No retrieval module exists yet** — this is the state Constitution I requires.

---

## Phase 3: User Story 1 — Rebuildable index (Priority: P1) 🎯 MVP

**Goal**: Turn the validated corpus into a searchable index with one command that rebuilds cleanly
every time, survives a mid-build failure, and refuses to serve stale content.

**Independent Test**: Build the index, rebuild it and confirm identical content with no traces of a
deleted runbook, edit a runbook and confirm staleness is detected. Entirely offline via `--no-embed`.

**Covers**: US1 acceptance scenarios 3–4 (scenarios 1–2 were satisfied by T012 + T022).

### Tests for User Story 1

> Write these first and confirm they fail before implementing T034–T040.

- [ ] T031 [P] [US1] Write `tests/test_chunk.py`: `chunk_fixed` window boundaries at size 800 / overlap 150 including the short-input and exact-multiple cases; `chunk_by_section` yielding exactly 6 chunks per runbook with the `"[{title}] [{category}] {section}: "` prefix present in `text`
- [ ] T032 [P] [US1] Write `tests/test_bm25.py`: `TSV_TNEW_PAGE_ALLOC_FAILED` and `SM37` surviving as whole tokens, `RC=8` splitting per the `[A-Za-z0-9_/]+` rule, Thai input yielding **zero** tokens (research.md R-05), and `rare_tokens()` boundaries — in-corpus error code qualifies, in-corpus common word does not, out-of-corpus error code does not
- [ ] T033 [P] [US1] Write `tests/test_store.py`: `chunks.jsonl` line ↔ `embeddings.npy` row alignment assertion, `StaleIndexError` on a `corpus_sha` mismatch, and a `--no-embed` manifest (`n_vectors == 0`) accepted for `bm25` while raising for `dense`

### Implementation for User Story 1

- [ ] T034 [P] [US1] Implement `chunk_fixed(text, size=800, overlap=150)` in `app/retrieval/chunk.py` as a pure function — the naive default matching the course reference app, producing the R-Dense-naive baseline (FR-011)
- [ ] T035 [P] [US1] Implement `chunk_by_section(runbook)` in `app/retrieval/chunk.py`: one `Chunk` per section with `chunk_id = "{doc_id}#{section_lower}"` and the context prefix prepended to `text` (FR-010, FR-011)
- [ ] T036 [US1] **Constitution I gate** — verify `git log` shows `eval/cases_dev.jsonl`, `eval/cases_test.jsonl`, and `eval/metrics.py` committed in earlier commits than `app/retrieval/chunk.py`; if not, stop and reorder the history before continuing
- [ ] T037 [US1] Implement `app/retrieval/bm25.py`: the `[A-Za-z0-9_/]+` lower-casing tokenizer and a `BM25Okapi` wrapper built over chunk texts (FR-016)
- [ ] T038 [US1] Implement `rare_tokens(query)` in `app/retrieval/bm25.py` exactly per research.md R-03: a token qualifies when it is present in the corpus BM25 vocabulary **and** either matches `^[A-Z][A-Z0-9_]{5,}$` in original casing or is a key of `data/tcodes.json`
- [ ] T039 [US1] Implement `app/retrieval/ingest.py:build_index(strategy, embed=True)`: load and validate the corpus, chunk, write `chunks.jsonl` + `manifest.json` (+ `embeddings.npy` when embedding) into `data/index.tmp/`, then atomically replace `data/index/`; on any failure discard the temp directory leaving the previous index intact (FR-008, FR-009, research.md R-04)
- [ ] T040 [US1] Implement `app/retrieval/store.py:Store.load()`: read `chunks.jsonl`, `manifest.json`, and the matrix when present; assert `len(chunks) == shape[0]` and `shape[1] == manifest.embed_dim`; recompute `corpus_sha` and raise `StaleIndexError` naming `python -m app.cli ingest` on mismatch; expose a BM25 ranked search (FR-010, FR-020)
- [ ] T041 [US1] Implement the `ingest` subcommand in `app/cli.py` with `--strategy`, `--no-embed`, `--quiet` and the exact summary block from contracts/cli.md (runbook count, category count, section count, allow-list size, strategy, embeddings/cache line, `corpus_sha`, commit) so an incomplete build is visible (FR-012); exit codes 0/2/3/4
- [ ] T042 [P] [US1] Write `tests/test_cli_boundary.py` asserting no module under `app/retrieval/` or `eval/` imports `app.cli` — the core and the eval never depend on an edge (Constitution VI)

**Checkpoint**: `python -m app.cli ingest --no-embed` builds offline; rebuilding is byte-identical;
a deleted runbook leaves no traces; an edited runbook is detected as stale. **SC-007 met.**

---

## Phase 4: User Story 2 — One command reports retrieval quality (Priority: P1)

**Goal**: A single command that reports recall@3, MRR, out-of-scope rejection and false-refusal rate
on the test set, with the configuration recorded beside the numbers — **working with no network**.

**Independent Test**: With no API key set, build a `--no-embed` index and run the harness in `bm25`
mode; a complete results file appears with all four metrics and a per-case breakdown. Run it twice
and the retrieval metrics are identical.

**Note**: this phase implements a minimal `search(mode="bm25")` because US2's own independent test in
spec.md requires "a deliberately naive keyword-only search". Dense and hybrid arrive in US3.

### Tests for User Story 2

- [ ] T043 [P] [US2] Write `tests/test_normalize.py`: timestamp and memory-address stripping, the 2000-character query cap truncating rather than raising, and key-token extraction for a runtime-error name, `RC=8`, a T-code, and a job name
- [ ] T044 [P] [US2] Write the `bm25` branch of `tests/test_gate.py`: empty `rare_tokens` returns `[]`, a single rare token admits results, and raising `min_score` never increases the result count (FR-018, US3 scenario 3)

### Implementation for User Story 2

- [ ] T045 [US2] Implement `app/normalize.py` as pure functions: `strip_noise()` (timestamps, `0x…` memory addresses, repeated blank lines), `cap_length(text, limit=2000)` truncating with a flag, and `extract_key_tokens()` using the regexes from `docs/prepare/04_system_flow.md` § B2 — `Runtime Errors\s+(\w+)`, `RC\s*=?\s*(\d+)`, T-code pattern, job name, first English error line (research.md R-10)
- [ ] T046 [US2] Implement `search(query, *, mode, k, min_score, store=None) -> list[Hit]` in `app/retrieval/search.py` with the six-step pipeline from contracts/search.md: validate (raise `InvalidQueryError` below 10 stripped characters or whitespace-only) → normalize and append key tokens → retrieve → collapse to best chunk per `doc_id` → gate → take `k` and assign contiguous 1-based `rank` (FR-013, FR-014, FR-015, FR-019)
- [ ] T047 [US2] Implement the `bm25`-mode gate in `app/retrieval/search.py`: return `[]` when `rare_tokens(query)` is empty, with no cosine consulted and no gateway client constructed (FR-017, FR-018, research.md R-02)
- [ ] T048 [US2] Implement the `search` subcommand in `app/cli.py` per contracts/cli.md: positional query or `--file`, `--mode`, `--k`, `--min-score`, `--json`, `--show-tokens`; human output showing `doc_id#section`, the score actually ranked by, category and snippet; results to stdout, errors to stderr; exit codes 0/2/3/4/5
- [ ] T049 [US2] Implement `eval/run_retrieval.py`: run one configuration over one split and write `eval/results/{experiment}_{config_slug}.json` with the full `config` block including `corpus_sha` and `git_commit` copied from the loaded manifest, plus per-case `CaseResult` entries (data-model.md § 9, FR-031, FR-035)
- [ ] T050 [US2] Compute **both** pre-gate and post-gate `recall_at_3` and `mrr` in `eval/run_retrieval.py`, plus `oos_gate_accuracy`, `false_refusal_rate`, and the `by_difficulty` slices for easy/medium/hard/thai/mixed/oos (research.md R-01, FR-032)
- [ ] T051 [US2] Abort the run in `eval/run_retrieval.py` when the loaded manifest's `chunk_strategy` disagrees with the requested `RunConfig.chunk_strategy`, rather than mislabelling the result (data-model.md § 9)
- [ ] T052 [US2] Produce and commit the first real test-set result offline: `python -m app.cli ingest --strategy section --no-embed` then `python -m eval.run_retrieval --split test --mode bm25 --strategy section --name R-BM25` (SC-012, quickstart.md step 4)
- [ ] T053 [P] [US2] Re-run T052's command unchanged and confirm the retrieval metrics are identical; record the check in `eval/results/` (FR-036, SC-004)

**Checkpoint**: a real recall@3 exists for the test set, produced with no network and no embedding
code. **SC-012 met; US2 independently testable.** This is the point at which the gateway going down
can no longer sink the project.

---

## Phase 5: User Story 3 — Cited sections, or a clear refusal (Priority: P1)

**Goal**: Complete the search capability — dense and hybrid retrieval, the real relevance gate, and
an explicit "nothing relevant" for logs the corpus does not cover.

**Independent Test**: Search a known dump and get resolvable `doc_id#section` citations; search a
HANA log-volume-full alert and get `NO_RELEVANT_RUNBOOK` with zero hits and exit code 0.

### Tests for User Story 3

- [ ] T054 [P] [US3] Write `tests/test_llm_cache.py` with a mocked OpenAI client: input order preserved (`data[i] ↔ input[i]`), `len(vector) == 1024` asserted, batching, a second call served entirely from `data/cache/` with zero client calls, and gateway errors surfacing as `UpstreamError`
- [ ] T055 [P] [US3] Write `tests/test_fusion.py`: RRF `Σ 1/(60 + rank)` against hand-computed ranks, and correctness when the dense list is empty, when the BM25 list is empty (the normal Thai case — research.md R-05), and when both are
- [ ] T056 [P] [US3] Extend `tests/test_gate.py` with the dense and hybrid branches: low cosine plus no rare token returns `[]`; low cosine plus a rare token admits results; high cosine admits regardless; and the gate reads `dense_score`, never the RRF score (research.md R-02)

### Implementation for User Story 3

- [ ] T057 [US3] Implement `app/llm.py:embed(texts)` as the **only** gateway caller in the project (Constitution VI): `OpenAI()` against `OPENAI_BASE_URL` with model `bge-m3`, batched, preserving input order, asserting `len(vector) == 1024`, wrapping SDK and proxy failures in `UpstreamError`
- [ ] T058 [US3] Add the disk cache to `app/llm.py`: key `sha256(f"{model}|{text}")` under `data/cache/`, written as `{"model","dim","vector"}` JSON, consulted before every call, reporting hit/miss counts to the caller for the ingest summary (research.md R-09, FR-036)
- [ ] T059 [US3] Add the embedding step to `app/retrieval/ingest.py`: embed all chunk texts, L2-normalise row-wise, write `float32` `embeddings.npy` aligned to `chunks.jsonl` line order, and populate `embed_model`, `embed_dim`, `n_vectors` in the manifest (contracts/file-formats.md §§ 4, 5)
- [ ] T060 [US3] Add cosine search to `app/retrieval/store.py`: a single `numpy` dot product of the normalised query vector against the normalised matrix — brute force, no index structure (Constitution VI)
- [ ] T061 [US3] Add `dense` mode to `app/retrieval/search.py`, embedding the normalised query through `app.llm.embed` and populating `Hit.dense_score`
- [ ] T062 [US3] Implement `fuse_rrf(dense_ranked, bm25_ranked, k=60)` in `app/retrieval/search.py`, fusing over **ranks** not raw scores, tolerant of an empty input list (research.md R-05)
- [ ] T063 [US3] Add `hybrid` mode to `app/retrieval/search.py`, populating `fused_score` alongside both component scores so the gate can read the cosine
- [ ] T064 [US3] Implement the `dense`/`hybrid` gate in `app/retrieval/search.py`: return `[]` when dense top-1 cosine `< min_score` **and** `rare_tokens(query)` is empty (FR-018, research.md R-02); add stable tie-breaking on `chunk_id` for equal scores (contracts/search.md guarantee 6)
- [ ] T065 [US3] Implement the refusal output in `app/cli.py`: `NO_RELEVANT_RUNBOOK`, the floor used, the best dense score, the rare tokens seen, the "not covered by the runbooks" line, and **exit code 0** — a correct refusal is a success (FR-018, SC-008)
- [ ] T066 [US3] Add a citation-resolvability check to `eval/run_retrieval.py` asserting every returned `chunk_id` resolves to existing corpus text, and run it across both splits to confirm zero dangling addresses (FR-010, SC-005)

**Checkpoint**: all three modes work; cited hits resolve; uncovered logs are refused explicitly.
**SC-005 and SC-008 met; all three P1 stories complete — this is the demonstrable MVP.**

---

## Phase 6: User Story 4 — Compare strategies by number (Priority: P2)

**Goal**: One-variable-at-a-time comparisons against named baselines, in tables that name the varied
variable and state the verdict honestly.

**Independent Test**: Run the comparison and confirm each row differs from its baseline in exactly
one named variable, all rows share a split and `corpus_sha`, and the table names a winner by number.

- [ ] T067 [US4] Implement experiment E1 in `eval/run_all.py`: `fixed-800/150` versus `section` chunking with mode `dense` and `k=3` held constant, reporting **pre-gate** recall@3 and MRR, dev then test, with the varied variable named in the output (FR-037, research.md R-01)
- [ ] T068 [US4] Implement experiment E2 in `eval/run_all.py`: `bm25` versus `dense` versus `hybrid` on E1's winning chunking, **pre-gate**, with `R-BM25` and `R-Dense-naive` marked as the named baselines (FR-038)
- [ ] T069 [US4] Implement the comparison view in `eval/run_all.py` computing per-metric deltas against each row's baseline, and refusing to emit a table whose rows disagree on `split` or `corpus_sha` (data-model.md § 10)
- [ ] T070 [US4] Generate the E1 and E2 tables into `eval/results/results.md`, every header labelled pre-gate, each row stating its baseline, and the BM25 row flagged as gated by the rare-token rule alone (research.md R-02, contracts/file-formats.md § 10)

**Checkpoint**: the chunking and retrieval claims in the report are backed by reproducible tables.
**SC-010 met.**

---

## Phase 7: User Story 5 — Tune the relevance floor on dev cases (Priority: P2)

**Goal**: Choose `MIN_SCORE` from a documented dev-set sweep showing the trade-off between rejecting
out-of-scope logs and wrongly rejecting in-scope ones — with the test set mechanically out of reach.

**Independent Test**: Run the sweep, confirm one row per floor value with both rates, and confirm it
raises if handed the test split.

- [ ] T071 [US5] Implement `sweep_min_score(split)` in `eval/run_all.py` as experiment E3: floors 0.30 to 0.60 in steps of 0.05 on the configuration from E2, reporting **post-gate** in-scope recall@3 and out-of-scope rejection rate per value; raise `ValueError` for any `split` other than `"dev"` (FR-039, FR-041, research.md R-01)
- [ ] T072 [P] [US5] Write `tests/test_sweep_guard.py` asserting `sweep_min_score("test")` raises and that no code path in the sweep loads `eval/cases_test.jsonl` (FR-041, SC-009)
- [ ] T073 [US5] Generate the E3 table into `eval/results/results.md` with the chosen `MIN_SCORE` and the identifier of the sweep run it came from, and update `.env.example`'s `MIN_SCORE` to the measured value (FR-040, SC-009)
- [ ] T074 [US5] Generate the headline test-set table into `eval/results/results.md`: the final configuration, **post-gate**, with out-of-scope gate accuracy and false-refusal rate reported for the chosen floor, unchanged from the dev sweep (FR-040, SC-009)

**Checkpoint**: the refusal threshold is justified by evidence, and the test set has not been tuned
against. **SC-009 met.**

---

## Phase 8: User Story 6 — Failures list explaining each wrong result (Priority: P3)

**Goal**: Turn bad numbers into understanding — every wrong case recorded with expected versus
retrieved and a failure type.

**Independent Test**: Force a failure with a deliberately high floor and confirm the affected cases
appear once each with full detail and a failure type.

- [ ] T075 [US6] Implement the `failures.jsonl` writer in `eval/run_retrieval.py` per data-model.md § 11: one record per wrong case with `case_id`, `config_name`, expected category and docs, `acceptable_docs` for context, `retrieved` in returned order, `failure_type`, and the case `note`; classify as `retrieval_miss` / `gate_false_refusal` / `gate_missed_oos` / `partial_recall` (FR-042)
- [ ] T076 [US6] Truncate `eval/results/failures.jsonl` at the start of each `eval/run_all.py` invocation and always create it, even when empty (FR-043)
- [ ] T077 [P] [US6] Write `tests/test_failures.py` asserting a case retrieving only `acceptable_docs` is recorded as `retrieval_miss` **only** when no `gold_doc` was found, and that matching an acceptable alternative is never itself a failure (FR-034)
- [ ] T078 [US6] Generate the remaining `eval/results/results.md` sections: the run header (`corpus_sha`, commit, embed model, date, splits), the per-difficulty slices including the Thai and mixed rows, the verdict sentence stated plainly whether or not hybrid wins, and the Limitations block covering synthetic logs, the 16-runbook corpus, single-author bias, and Thai contributing nothing to BM25 (FR-044, SC-014, research.md R-05)

**Checkpoint**: every number in the report is traceable, and every failure is explained.
**SC-011 and SC-014 met; all six stories complete.**

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T079 Write `README.md` with what/why, setup, ingest, search, eval, the result tables, and the limitations — the path a newcomer follows end to end (Constitution IX, FR-031)
- [ ] T080 [P] Measure single-search wall-clock time in `hybrid` mode and record it in `README.md`; confirm under 3 seconds (SC-013)
- [ ] T081 Walk `specs/001-runbook-retrieval-eval/quickstart.md` steps 0–9 on a clean clone and fix any divergence between the documented and actual behaviour (Constitution IX)
- [ ] T082 Commit all of `eval/results/` — per-config json, `failures.jsonl`, `results.md` — so every reported number ships with the config that produced it (Constitution I)
- [ ] T083 Re-check this feature against Constitution I–X and record the outcome in `specs/001-runbook-retrieval-eval/plan.md` § Post-Design Re-Check, noting any principle the implementation strained
- [ ] T084 [P] Create `examples/` with three sample **logs** (not runbooks): `examples/tsv_dump.log` for the success demo, `examples/hana_disk_full.log` for the out-of-scope refusal, and `examples/mixed_lock_update.log` for the failure demo — the three scenes the demo script in `docs/prepare/10_timeline_and_checklist.md` § 5 calls for, and the file the README quickstart references

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup — **blocks every user story**
- **US1 (Phase 3)**: depends on Foundational
- **US2 (Phase 4)**: depends on US1 (needs a built index to search)
- **US3 (Phase 5)**: depends on US2 (completes `search()`; US2 established the pipeline and the harness)
- **US4 (Phase 6)**: depends on US3 (E2 needs all three modes)
- **US5 (Phase 7)**: depends on US4 (E3 sweeps the configuration E2 selected)
- **US6 (Phase 8)**: depends on US2 (the harness emits failures); content is richest after US5
- **Polish (Phase 9)**: depends on all desired stories

### Deviation from the template's parallel-stories model

These stories are **not** mutually independent, and the plan does not pretend otherwise. US2 needs an
index, US3 completes the function US2 began, US4 needs US3's modes, and US5 needs US4's winner. That
is inherent to a measurement pipeline: each stage measures the previous one. What each story *does*
preserve is the template's real requirement — an independently **testable** increment, with a
checkpoint that can be validated and demonstrated on its own.

### Within Each User Story

- Tests are written first and must fail before the implementation tasks in the same phase
- Schemas before parsers; parsers before chunkers; chunkers before the store; store before search
- `search()` before the harness; the harness before the experiments
- Commit after each task or logical group — small, incremental commits (Constitution IX)

### Parallel Opportunities

- T003 + T004 (Setup); T006 alongside T005
- **T014–T021** — all 8 runbook-pair tasks are independent files and the largest parallel block in the feature
- T009 alongside T008; T030 alongside T029
- T031 + T032 + T033 (US1 tests); T043 + T044 (US2 tests); T054 + T055 + T056 (US3 tests)
- T034 + T035 (both chunkers, same file — coordinate or serialise)
- T042, T053, T072, T077, T080 are independent checks

---

## Parallel Example: Foundational corpus authoring

```bash
# The 8 runbook-pair tasks touch disjoint files and can all proceed at once:
Task: "Write data/runbooks/mem_tsv_tnew_page_alloc.md and mem_system_no_roll.md"
Task: "Write data/runbooks/timeout_dialog.md and timeout_long_running_wp.md"
Task: "Write data/runbooks/job_cancelled.md and job_stuck_ready_released.md"
Task: "Write data/runbooks/lock_old_entries.md and lock_table_overflow.md"
Task: "Write data/runbooks/update_terminated.md and update_deactivated.md"
Task: "Write data/runbooks/transport_rc8.md and transport_rc12_or_stuck.md"
Task: "Write data/runbooks/user_locked.md and auth_missing.md"
Task: "Write data/runbooks/rfc_connection_failed.md and rfc_trfc_queue.md"
```

## Parallel Example: User Story 3 tests

```bash
Task: "Write tests/test_llm_cache.py with a mocked OpenAI client"
Task: "Write tests/test_fusion.py including empty-list inputs"
Task: "Extend tests/test_gate.py with the dense and hybrid branches"
```

---

## Implementation Strategy

### MVP scope

The honest MVP is **all three P1 stories: US1 + US2 + US3** (through T066). US1 alone builds an index
nobody can query; US2 alone measures a keyword-only search. The spec's own framing — "a searchable,
measured runbook corpus" — needs all three, and Constitution VII's priority chain places retrieval
before the agent precisely so that this much is finished first.

If time collapses, the defensible stopping point is **T053** (end of US2): a committed, reproducible
recall@3 on the test set from a keyword-only search, with every number traceable. That is a real
result honestly reported, which Principle II values over an unmeasured hybrid.

### Incremental delivery

1. Setup + Foundational → corpus and eval set committed, all offline tests green
2. US1 → index builds cleanly and detects staleness · **SC-007**
3. US2 → first reproducible recall@3, no network needed · **SC-004, SC-012**
4. US3 → cited hits and explicit refusals · **SC-005, SC-008** · *demonstrable MVP*
5. US4 → chunking and mode comparisons · **SC-010**
6. US5 → justified relevance floor · **SC-009**
7. US6 → failures and honest reporting · **SC-011, SC-014**
8. Polish → README, quickstart rehearsal, committed results

### Single-author note

The template's parallel-team strategy does not apply — spec.md names one maintainer. The [P] markers
are therefore about *safe reordering* (disjoint files, no incomplete dependencies), which matters most
in the T014–T021 corpus block where authoring can be interleaved with reading source material.

---

## Notes

- 84 tasks: 6 Setup, 24 Foundational, 12 US1, 11 US2, 13 US3, 4 US4, 4 US5, 4 US6, 6 Polish
- `[P]` = disjoint files, no dependency on an incomplete task
- Field constraints are quoted verbatim from data-model.md so no rule is left to implementation-time
  discretion
- T036 is a history gate, not code — it is the only real evidence for Principle I
- Verify each phase's tests fail before implementing that phase
- Stop at any checkpoint to validate the increment independently
