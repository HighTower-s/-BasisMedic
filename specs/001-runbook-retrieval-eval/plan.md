# Implementation Plan: Runbook Corpus, Labelled Eval Set, and Measured Retrieval

**Branch**: `001-runbook-retrieval-eval` | **Date**: 2026-11-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-runbook-retrieval-eval/spec.md`

## Summary

Build the measurable foundation of BasisMedic: 16 hand-written SAP Basis runbooks with a T-code
allow-list, a 40-case labelled evaluation set authored *before* any search code, and a hybrid
retrieval stack (BM25 + bge-m3 dense + RRF) whose quality is reported by one command against named
baselines.

Technical approach: a small layered Python package. `app/retrieval/runbooks.py` parses and validates
the corpus; `chunk.py` offers two strategies (naive fixed-size vs section-aligned) so chunking can be
ablated; `ingest.py` builds an index atomically into `data/index/` (chunks, normalised embedding
matrix, manifest); `store.py` holds the brute-force cosine and BM25 lookups; `search.py` is the single
service entry point `search(query, mode, k, min_score) -> list[Hit]` shared by the CLI and the eval
harness. `app/llm.py` is the only module that touches the gateway, exposing `embed(texts)` with a
disk cache so repeated runs produce identical numbers. `eval/` holds the two case files, pure metric
functions, a single-config runner, and `run_all.py`, which executes experiments E1–E3 one variable at
a time and writes committed results plus a failures log.

No chat model is used in this feature at all — retrieval and measurement only.

## Technical Context

**Language/Version**: Python 3.12 (matches the course reference app's `requires-python >=3.12`)

**Primary Dependencies**: `openai>=1.40` (embeddings via the course gateway only), `numpy>=1.26`
(brute-force cosine), `rank-bm25>=0.2.2` (`BM25Okapi`), `pydantic>=2.7` (corpus and eval-case
validation). Dev: `pytest>=8.0`. Managed with `uv` (`pyproject.toml` + `uv.lock`).

**Explicitly not used**: any LLM orchestration framework (LangChain/LlamaIndex), any vector database
or Postgres/pgvector, any reranker, any non-gateway model provider.

**Storage**: plain files. Committed: `data/runbooks/*.md`, `data/tcodes.json`, `eval/cases_*.jsonl`,
`eval/results/*`. Generated: `data/index/{chunks.jsonl,embeddings.npy,manifest.json}` (rebuilt
wholesale), `data/cache/` (embedding cache, git-ignored).

**Testing**: `pytest`, fully offline. Every test runs with no network; the gateway is mocked at the
single `app.llm.embed` seam.

**Target Platform**: local developer machine (Windows 11 for the author; no OS-specific code — paths
via `pathlib`, no shell assumptions).

**Project Type**: single Python package with a CLI edge plus an evaluation harness. No service, no UI.

**Performance Goals**: a single search over the full corpus returns in under 3 seconds wall-clock
(SC-013), dominated by one query-embedding round-trip to the gateway. BM25-only mode must return in
well under 1 second with no network. Full `run_all.py` completes in minutes, not hours, because
embeddings are cached after the first build.

**Constraints**: no secrets in the repository; all configuration from environment variables read in
exactly one module (`app/config.py`); the embedding call in exactly one module (`app/llm.py`);
BM25-only paths must work with no network access (FR-017, SC-012); two consecutive eval runs must
produce identical retrieval metrics (FR-036, SC-004).

**Scale/Scope**: 16 runbooks × 6 sections ≈ 96 chunks under section chunking (≈ 60–80 under fixed-800
chunking); 1024-dimension vectors, so the whole embedding matrix is ≈ 400 KB. 10 dev + 30 test cases.
Single author, single machine, no concurrency.

### Decisions carried in from the spec and the clarify session

The `/speckit-clarify` session was interrupted after one question and recorded no clarifications in
`spec.md`. One queued question remains materially open and is resolved in
[research.md](./research.md) rather than left as an unknown:

- **Is recall@3 measured before or after the relevance gate?** Resolved as R-01: measure and report
  **both**. Strategy comparisons (E1/E2) use pre-gate recall so the varied variable stays isolated;
  the headline test table and the E3 sweep use post-gate recall. Every table labels which it shows.
  Overrule this if you disagree — it changes metric semantics, not code structure.

No `NEEDS CLARIFICATION` markers remain in this Technical Context.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v1.0.0. Gate status: **PASS** (initial), **PASS** (re-checked post-Phase 1 — see
[Post-Design Re-Check](#post-design-re-check)).

| Principle | How this plan satisfies it | Gate |
|---|---|---|
| **I. Evaluation-First** | `eval/cases_dev.jsonl` and `eval/cases_test.jsonl` plus their validator are authored and committed **before** `chunk.py`, `store.py`, or `search.py` exist (enforced by task ordering, FR-021). `eval/metrics.py` and the BM25-only path land next, so recall@3/MRR are measurable before any embedding code. Named baselines R-BM25 and R-Dense-naive are first-class configs in `run_all.py`; E1/E2/E3 each change exactly one variable. E3 sweeps `MIN_SCORE` on **dev only** — the sweep API accepts `split="dev"` and raises otherwise, with a unit test proving it. `uv run python -m eval.run_all` reproduces every number and writes config (incl. `corpus_sha` and git commit) next to the metrics. | PASS |
| **II. Honest Reporting** | Every failing case is written to `eval/results/failures.jsonl` with expected vs retrieved and a failure type; the file is created even when empty (FR-043). `results.md` is generated from run artifacts only — never hand-edited — and prints the comparison verdict including "combined did not win" when that is the outcome. Every eval case carries `synthetic: true`; `results.md` carries a standing Limitations block (corpus size, single-author bias, Thai/BM25 interaction, synthetic logs). | PASS |
| **III. Grounded Answers Only** | Retrieval reads only `data/runbooks/*.md`. Every `Hit` carries `chunk_id = "{doc_id}#{section}"` resolvable to real corpus text, and a unit test asserts zero dangling ids across both splits (SC-005). T-codes come from `data/tcodes.json`; `ingest` fails loudly on a corpus T-code absent from the allow-list (SC-006). When nothing clears the gate, `search()` returns `[]` — and because no chat model is wired in this feature, there is structurally no path by which a model could guess. | PASS |
| **IV. Untrusted Model and Inputs** | No model output is consumed in this feature, so the schema/repair machinery is out of scope here. What does apply: corpus front-matter and eval cases are parsed through Pydantic v2 models that fail loudly with the offending file/case named (FR-007, FR-030); query length is validated at the edge before any search (FR-019); `app/llm.py` wraps gateway failures in `UpstreamError` rather than leaking SDK exceptions; no tools and no agent loop exist yet, so no loop bound is needed. Determinism: embeddings are cached, not sampled. | PASS |
| **V. Course Constraints** | `openai` SDK only, `OpenAI()` against `OPENAI_BASE_URL`, embedding model `bge-m3`. No chat model called. All config from env via `app/config.py`; `.env.example` committed, `.env` git-ignored; no key in any committed file. No orchestration framework. Differentiation from the reference app: own SAP Basis corpus, own 40-case eval set, hybrid BM25+dense retrieval with RRF, section-aligned chunking measured against the reference's naive fixed-800 default. | PASS |
| **VI. Layered, Simple Architecture** | Edge `app/cli.py` (arg parsing and printing only) → service `app/retrieval/search.py` → repository `app/retrieval/store.py` / `runbooks.py` / `data/tcodes.json`. Dependencies point inward; nothing in `app/retrieval/` or `eval/` imports the CLI. The embedding call lives only in `app/llm.py`. Brute-force cosine over a ≈96×1024 matrix — no index structure, no database. **One correction to the input plan**: the CLI moves out of `search.py` into `app/cli.py` (see [Structure Decision](#structure-decision)). | PASS |
| **VII. Scope Discipline** | This feature is position 1–2 of the constitutional build order (eval set → retrieval). Nothing downstream is started: no agent, no structured triage output, no API, no UI — all listed in the spec's Out of Scope and absent from the task plan. Task ordering within the feature follows the same discipline: corpus → eval set → metrics → BM25 → harness → dense → hybrid → experiments. | PASS |
| **VIII. Testing** | Deterministic units get offline tests: runbook parser/validator, both chunkers, BM25 tokenizer, RRF fusion, gate rule, all four metrics (hand-computed fixtures), `normalize`, eval-case validator (counts, distribution, coverage, 8-word-span check), store load/cosine, and the dev-only sweep guard. Answer quality is measured by `run_all.py`, never asserted in a unit test. | PASS |
| **IX. Runnable from README, Incremental History** | `quickstart.md` is the rehearsal of the README path: `uv sync` → copy `.env.example` → `uv run python -m app.cli ingest` → `search` → `uv run python -m eval.run_all`. Each task in the plan is a small commit; the eval set is committed before retrieval code, which `git log` will show. | PASS |
| **X. Content and Licensing** | Runbooks are written in the author's own words in English from `docs/prepare/07_short_dump_and_incidents.md`, each with a `references:` URL list surfaced as the `## References` section; the parser requires at least one reference URL (FR-002). No SAP Notes text, no long SAP documentation passages. No UI in this feature, so no branding surface. | PASS |

**Initial gate result: PASS — no unjustified violations.** Three additions beyond "the simplest thing
that works" are recorded in [Complexity Tracking](#complexity-tracking) with their justification.

## Project Structure

### Documentation (this feature)

```text
specs/001-runbook-retrieval-eval/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output — 12 resolved design decisions
├── data-model.md        # Phase 1 output — entities, schemas, validation rules
├── quickstart.md        # Phase 1 output — runnable validation walkthrough
├── contracts/           # Phase 1 output
│   ├── cli.md           #   CLI command contract (ingest, search)
│   ├── search.md        #   search() service contract + Hit shape
│   └── file-formats.md  #   runbook, tcodes, chunks, manifest, case, results schemas
├── checklists/
│   └── requirements.md  # Spec quality checklist (from /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
pyproject.toml           # uv-managed; deps per Technical Context
uv.lock
.env.example             # committed; .env git-ignored
.gitignore               # data/index/, data/cache/, .env

app/
├── __init__.py
├── config.py            # the ONLY reader of environment variables
├── llm.py               # the ONLY caller of the gateway: embed(texts) + UpstreamError
├── schemas.py           # Pydantic: Runbook, TcodeEntry, Chunk, Hit, IndexManifest
├── normalize.py         # pure: strip noise, cap length, extract key tokens
├── cli.py               # EDGE: `python -m app.cli ingest|search` — parse + print only
└── retrieval/
    ├── __init__.py
    ├── runbooks.py      # REPOSITORY: parse + validate data/runbooks/*.md, load tcodes.json
    ├── chunk.py         # pure: chunk_fixed(800,150) and chunk_by_section()
    ├── bm25.py          # tokenizer + BM25Okapi wrapper + rare-token set
    ├── store.py         # REPOSITORY: load index, cosine search, bm25 search
    ├── ingest.py        # build index atomically (tmp dir -> swap), write manifest
    └── search.py        # SERVICE: search(query, mode, k, min_score) -> list[Hit]

data/
├── runbooks/            # 16 committed .md files (2 per category x 8 categories)
├── tcodes.json          # committed T-code allow-list
├── index/               # GENERATED: chunks.jsonl, embeddings.npy, manifest.json
└── cache/               # GENERATED, git-ignored: embedding cache by sha256(model|text)

eval/
├── __init__.py
├── cases_dev.jsonl      # 10 cases — tuning only
├── cases_test.jsonl     # 30 cases — reporting only
├── schema.py            # Pydantic EvalCase + split-level validators
├── metrics.py           # pure: recall_at_k, mrr, gate_accuracy, false_refusal_rate
├── run_retrieval.py     # one config over one split -> results json + failures
├── run_all.py           # E1, E2, E3 in order -> eval/results/results.md
└── results/             # COMMITTED: per-run json, failures.jsonl, results.md

examples/                # sample LOGS for the README quickstart and the demo (never runbook text)
├── tsv_dump.log         #   success scene
├── hana_disk_full.log   #   out-of-scope refusal scene
└── mixed_lock_update.log#   failure scene

tests/
├── conftest.py          # tiny fake corpus + mocked embed() fixture
├── test_runbooks.py     test_chunk.py       test_bm25.py
├── test_fusion.py       test_gate.py        test_metrics.py
├── test_normalize.py    test_eval_cases.py  test_store.py
└── test_sweep_guard.py  # proves the min_score sweep refuses the test split
```

### Structure Decision

Single Python package, three layers, matching Constitution VI and the author's own target layout in
`docs/prepare/03_tech_stack.md` §4.

**One deliberate change from the input plan.** The input specified the CLI as
`python -m app.retrieval.search "<log>"` and `python -m app.retrieval.ingest`. Running `search.py` as
`__main__` makes that file simultaneously the service layer and the edge, which Constitution VI
forbids ("Edges MUST contain no business logic", dependencies inward only). The plan instead puts a
single thin edge in **`app/cli.py`** with subcommands:

```
uv run python -m app.cli ingest  [--strategy section|fixed]
uv run python -m app.cli search  "<log text>"   [--file path] [--mode ...] [--k 3] [--min-score 0.40]
```

`app/cli.py` parses arguments, calls `ingest.build_index()` or `search.search()`, and prints — no
logic of its own. This also matches `03_tech_stack.md` §4, which already lists `app/cli.py` as the
CLI edge, and gives Feature 2 a `triage` subcommand to add rather than a second CLI to invent. If you
prefer your original invocation, it is a one-line `__main__` shim per module — but then `search.py`
owns both layers, and the Constitution VI gate above would need a Complexity Tracking entry.

## Complexity Tracking

> Three items exceed "the simplest thing that works" (Constitution VI). Each is required by another
> principle, so none is an unjustified violation — but all are recorded here.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Two chunking strategies and three retrieval modes kept in the shipped code, not just in a throwaway experiment | Principle I requires every retrieval change to be measured against **named baselines** (R-Dense-naive = fixed-800 chunks; R-BM25 = keyword-only). A baseline that cannot be re-run is not a baseline, and `run_all.py` must reproduce all three rows on demand. | Hard-coding only the winning configuration would make the comparison tables unreproducible, breaking FR-031/FR-036 and SC-004. Deleting the losers after the fact would leave claims in the report that the repo cannot regenerate. |
| Disk embedding cache (`data/cache/`, keyed `sha256(model \| text)`) | FR-036 and SC-004 require two consecutive runs to yield **identical** retrieval metrics, and `run_all.py` re-embeds the same corpus across ~6 configurations. The cache makes repeat runs both deterministic and free. | Re-embedding per run costs gateway calls on every experiment and makes identical-numbers claims depend on upstream stability the project does not control. A pure in-memory cache would not survive between the separate processes `run_all.py` spawns per config. |
| Index manifest with corpus hash + atomic tmp-dir swap on build | FR-009 (clean rebuild), FR-020 (stale-index detection), FR-035 (results record the corpus version measured). A plain in-place "delete then write" is not crash-safe: a gateway failure mid-embed destroys the working index and leaves nothing. | Deleting in place satisfies FR-009's letter but leaves the author with no index after any mid-build failure, and gives no way to detect that an index predates an edited runbook — silently scoring eval against stale text, which is exactly the dishonest-number failure Principle II exists to prevent. |

## Phase 0 — Research

See [research.md](./research.md). Twelve decisions, each with rationale and rejected alternatives. The
four that most affect implementation:

- **R-01** Recall measured both pre-gate and post-gate, each labelled (resolves the open clarify question).
- **R-02** The gate is mode-specific. The input plan's rule ("dense top-1 cosine `< MIN_SCORE` **and** no
  rare-token match") cannot run in `bm25` mode, which has no cosine — yet FR-017/SC-012 require the
  BM25 path to work with no network. Resolved: dense/hybrid gate on cosine + rare-token; `bm25` mode
  gates on the rare-token rule alone, and that weaker gate is labelled in the results table.
- **R-03** "Rare token" given a concrete, testable definition: a query token that is present in the
  corpus BM25 vocabulary **and** either matches `^[A-Z][A-Z0-9_]{5,}$` (runtime-error shape) or is a
  key in `data/tcodes.json`.
- **R-05** Thai queries score **zero** under the `[A-Za-z0-9_/]+` tokenizer, so Thai cases are carried
  entirely by the dense side and hybrid must tolerate an empty BM25 list. This is a predicted,
  reportable finding rather than a bug to hide.

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — the 11 spec entities as concrete Pydantic models and file
  schemas, with every validation rule traced to its FR.
- [contracts/cli.md](./contracts/cli.md) — command surface, arguments, exit codes, output shape.
- [contracts/search.md](./contracts/search.md) — `search()` signature, `Hit` shape, gate semantics,
  ordering and de-duplication guarantees, error behaviour.
- [contracts/file-formats.md](./contracts/file-formats.md) — runbook front-matter + sections,
  `tcodes.json`, `chunks.jsonl`, `manifest.json`, eval case line, results json, `failures.jsonl`.
- [quickstart.md](./quickstart.md) — the runnable validation path a newcomer follows, with the
  expected observable outcome of each step mapped to its success criterion.

### Post-Design Re-Check

Re-evaluated after writing the Phase 1 artifacts. Still **PASS** on all ten principles. Two points
the design work changed:

1. **Principle VI held under pressure.** Defining the `search()` contract exposed that de-duplication
   to distinct documents must happen inside the service (FR-015 applies to every caller), not only in
   the eval harness as the input plan's wording implied. Keeping it in `search()` leaves the CLI and
   the harness genuinely identical, preserving the single service path.
2. **Principle I gained a mechanical guard.** The dev-only sweep is enforced in code
   (`sweep_min_score(split)` raises on anything but `"dev"`) with `tests/test_sweep_guard.py`, rather
   than resting on the author's discipline. Spec FR-041 asked for the property; the design now makes
   violating it fail a test.

No new Complexity Tracking entries arose from Phase 1.

### Implementation Re-Check (post Phase 9, T083)

Re-evaluated against all ten principles after full implementation (Phases 3–9) and a literal
walkthrough of `quickstart.md`. Still **PASS** on all ten. Two real defects were found and fixed
during the walkthrough — recorded here because Principle II requires strained spots named, not
smoothed over:

1. **Principle I / II strained by a line-ending bug, now fixed.** `corpus_sha()` originally hashed
   raw file bytes. Git's `core.autocrlf` (set `true` on the author's machine) rewrites CRLF/LF on
   checkout, so a `git checkout` of an unmodified runbook silently produced a **different**
   `corpus_sha` than before — discovered live when a deliberate stale-index test (quickstart step
   7) reverted cleanly by `git diff` but still changed the hash. This directly threatened SC-004's
   reproducibility claim: the same logical corpus could hash differently across machines, OSes, or
   even repeated checkouts on one machine, which would silently invalidate every committed
   `corpus_sha` in `eval/results/*.json` on a clean clone. Fixed by hashing `read_text()` (universal
   newlines) instead of `read_bytes()` — content-based, not byte-representation-based. No committed
   result file needed re-measuring once fixed (the underlying content is unchanged, only the stable
   hash of it), but the index itself had to be rebuilt once to pick up the corrected hash.
2. **Principle VI's single-service-path assumption exposed an aliasing bug.** `eval/run_all.py`'s
   `INDEX_DIRS["section"]` originally aliased the main CLI's `data/index/` directory. That was
   silently correct only while `section` happened to be the shipped default; once E1's own measured
   result changed the default to `fixed` (Phase 7), the alias meant `get_store("section")` would
   load a `fixed`-chunked index and treat it as `section`-chunked — a real bug that `_assert_comparable`
   could not catch because it checks `corpus_sha`/`split` agreement, not chunk-strategy identity
   against the directory's name. Fixed by giving `run_all.py` its own dedicated
   `data/index_section/` / `data/index_fixed/` directories, fully decoupled from the CLI's
   `data/index/`. `get_store()` was also hardened to rebuild on `StaleIndexError`, not just on a
   missing manifest, so a future corpus edit does not silently fail the whole experiment run.

Neither defect changed any previously reported number — the measured recall@3/MRR/gate-accuracy
values are identical before and after both fixes, confirmed by re-running `eval/run_all.py` and
diffing the output. Both were caught specifically *because* T081 required running the documented
commands rather than reading the plan and assuming it matched the code.
