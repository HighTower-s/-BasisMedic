---

description: "Task list for Feature 002 — triage agent: bounded tool-calling loop with verified structured output"
---

# Tasks: Triage Agent — Bounded Tool-Calling Loop with Verified Structured Output

**Input**: Design documents from `/specs/002-triage-agent/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Test tasks **are** included. Constitution VIII mandates unit tests for every deterministic part with
`app.llm.chat` mocked, and plan.md § Constitution Check commits to them — so they are a requirement here, not an
option, same as Feature 1. Answer quality is measured by `eval/run_e2e.py`, never asserted in a unit test.

**Organization**: Tasks are grouped by user story. See the ordering note below for why several stories' "new
code" is thin — much of the robustness they describe is intrinsic to the module built in US1, and later phases
are mainly the dedicated tests that prove it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1–US5)
- Exact file paths are given in every task

## Path Conventions

Extends Feature 1's single Python project at the repository root: `app/` (gains `agent/`, extends `llm.py`,
`schemas.py`, `cli.py`), `eval/` (gains `run_e2e.py`, extends `run_all.py`), `data/` (gains `chat_cache/`),
`tests/`. No new top-level directory.

---

## ⚠️ Ordering note: why Foundational is small, and why US3/US5 are mostly tests

Unlike Feature 1, this feature needs **no new eval set** — Feature 1's committed `cases_dev.jsonl`/
`cases_test.jsonl` already carry `gold_tcodes` (confirmed in research.md), so Constitution I's eval-first gate was
already cleared before this feature's spec was written. Foundational here is just the shared schema and the
`chat()` seam every story needs.

US3 ("malformed output is repaired, then safely downgraded") and US5 ("every unverifiable claim is caught") are
largely *properties of modules US1 already builds* — `formatter.py`'s repair loop and `verify.py`'s checks are not
optional extras bolted on after US1's happy path; they are what makes `formatter.py`/`verify.py` correct at all.
Resolution, stated rather than hidden: US1's phase builds the full modules (happy path *and* repair/fallback
*and* verification, because they cannot be meaningfully separated without building a second formatter/verify
pair later). **US3 and US5's phases consist of the dedicated tests that force those paths and prove the
guarantee** — this is defensible on the template's own terms, since what matters is that each story is
*independently testable*, which these phases still are: T029–T031 and T045–T047 can be run and will pass (or
fail) without any other phase's tests existing.

Within the stories, order follows [research.md R-12](./research.md#r-12--task-ordering-metric-functions-and-the-agents-unit-tested-guarantees-come-before-real-wiring):
the parts whose correctness is fully knowable without ever calling a real model (`tools.py`, `verify.py`,
`fallback.py`) are built and tested before the parts that need `app.llm.chat` mocked (`loop.py`, `formatter.py`),
which are built before the service wiring (`triage_service.py`) and the CLI edge.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package skeleton for the new `app/agent/` module and the chat-cache git-ignore entry.

- [X] T001 Create `app/agent/__init__.py` (empty package marker, matching `app/retrieval/__init__.py`'s pattern)
- [X] T002 [P] Add `data/chat_cache/` to `.gitignore`, alongside the existing `data/cache/` entry (R-09) — generated, never committed

**Checkpoint**: `app/agent/` importable as a package; `data/chat_cache/` will never be accidentally committed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The structured-output schema every story validates against, and the chat-calling seam every story
that talks to the model needs. No eval-set work is needed here (see Ordering note above).

**⚠️ CRITICAL**: No user story work may begin until this phase is complete.

### Shared schema

- [X] T003 [P] Define `Confidence = Literal["high", "medium", "low"]` and `FailureTypeE2E = Literal["category_wrong", "tcode_recall_miss", "unverified_claim", "repair_exhausted", "loop_exhausted", "schema_invalid_after_fallback"]` in `app/schemas.py`, per data-model.md § Enumerations
- [X] T004 Define the `Step` Pydantic model in `app/schemas.py` per data-model.md § 1: `action: str` with `min_length=5`, `tcode: str | None` (validated against the allow-list only once `verify_tcodes` has run, not at construction time)
- [X] T005 Define the `TriageResult` Pydantic model in `app/schemas.py` per data-model.md § 2, quoted verbatim: `category: EvalCategory` (reuses Feature 1's enum as-is), `summary: str` with `max_length=300`, `tcodes: list[str]` with `max_length=6`, `unverified_tcodes: list[str]`, `steps: list[Step]` with `min_length=1, max_length=8`, `escalate_to: EscalateTo | None` (reuses Feature 1's enum), `sources: list[str]`, `confidence: Confidence`; add the model-level invariant `category == "out_of_scope"` ⇒ `tcodes == []` **and** `sources == []` (FR-012) as a `model_validator`
- [X] T006 [P] Write `tests/test_schemas_triage.py` covering T005's invariant (an `out_of_scope` result with non-empty `tcodes` or `sources` raises) and the field bounds from T004/T005 (a 4-char `action`, a 7-tcode list, a 9-step list, a 301-char summary each raise)

### Chat seam and cache

- [X] T007 Implement `app/llm.py:chat(messages, tools=None, temperature=0, model=None) -> dict`: the second and last function allowed to construct or call the gateway client (Constitution VI), using the same `OpenAI()` client Feature 1's `embed()` already constructs; defaults `model` to `config.chat_model()` (new accessor, below); wraps SDK and proxy failures in `UpstreamError`, reusing the exception Feature 1's `embed()` already raises
- [X] T008 [P] Add `chat_model() -> str` to `app/config.py` reading `CHAT_MODEL` (already reserved in `.env.example` at `gemma-4-E4B-it`, unused until now), following the same `_str()` pattern as `embed_model()`
- [X] T009 Add the disk cache to `app/llm.py:chat()` per research.md R-09: key `sha256(f"{model}|{temperature}|{json.dumps(messages, sort_keys=True)}|{json.dumps(tools or [], sort_keys=True)}")`, stored at `data/chat_cache/<key>.json` as `{"model", "temperature", "response"}` (contracts/file-formats.md § 2); a cache hit never calls the gateway
- [X] T010 [P] Write `tests/test_llm_chat_cache.py` with a mocked OpenAI client: a cache miss calls the client and writes the cache file; a second identical call (same model, temperature, messages, tools) is served entirely from `data/chat_cache/` with zero client calls; a call that differs only in `tools` or `temperature` is a cache miss (not silently served the wrong cached response); a gateway error surfaces as `UpstreamError`

**Checkpoint**: `TriageResult`/`Step` exist and are unit-tested in isolation; `app.llm.chat()` exists, is cached,
and is unit-tested with the SDK client mocked. **No agent logic exists yet** — this is the point Phase 3 builds
from.

---

## Phase 3: User Story 1 — A covered incident gets a verified, cited triage result (Priority: P1) 🎯 MVP

**Goal**: The full pipeline for an in-scope log: bounded tool-calling loop, formatter with its repair loop,
citation and T-code verification, deterministic fallback — everything that makes the happy-path result
trustworthy, built as complete modules (see Ordering note: the repair/fallback/verification logic is inseparable
from a correct `formatter.py`/`verify.py`, so it is built here, not deferred).

**Independent Test**: Triage a known in-scope log (one whose expected runbook is already labelled in Feature 1's
eval set) and confirm the returned category matches the label, every T-code is allow-listed, and every citation
resolves to evidence retrieved during that same run.

**Covers**: US1 acceptance scenarios 1–4.

### Tests for User Story 1

> Write these first and confirm they fail before implementing T016–T024.

- [X] T011 [P] [US1] Write `tests/test_agent_tools.py` per contracts/tools.md: `search_runbook` query length bounds (10–300 chars after stripping — outside that range returns a string error, never raises); `NO_RELEVANT_RUNBOOK` returned verbatim when the wrapped `search()` call returns `[]`; `lookup_tcode` code-shape validation against Feature 1's `TCODE_RE`; dispatch of an unknown tool name is never attempted; a malformed-argument call is never recorded as a `ToolCallRecord`
- [X] T012 [P] [US1] Write `tests/test_agent_verify.py` (happy-path branches only here; the forcing/fallback branches are T029/T045): `verify_citations` drops a citation whose `chunk_id` is not present in that request's Evidence and keeps one that is; `verify_tcodes` moves a code not on the allow-list into `unverified_tcodes` and keeps an allow-listed one in `tcodes`
- [X] T013 [P] [US1] Write `tests/test_agent_fallback.py`: the fallback `TriageResult` built from a single Evidence runbook always passes `TriageResult` validation; `confidence == "low"`; `category`/`tcodes`/`escalate_to` are copied from that runbook's own front-matter; `steps` are derived from that runbook's `## Check` section's numbered list (per research.md R-05)
- [X] T014 [P] [US1] Write `tests/test_agent_loop.py` (happy-path and bound-respecting branches only here; forced-stop-at-MAX_STEPS is T030): with `app.llm.chat` mocked, a model that calls `search_runbook` once then stops (no further tool calls) ends the loop after that one call and returns the gathered `ToolCallRecord`s as Evidence
- [X] T015 [P] [US1] Write `tests/test_agent_formatter.py` (happy-path branch only here; repair-loop and cap-exhaustion branches are T029): with `app.llm.chat` mocked to return well-formed JSON on the first attempt, the formatter returns a `TriageResult` with no repair attempts recorded

### Implementation for User Story 1

- [X] T016 [US1] Implement `app/agent/tools.py:search_runbook(args: dict) -> str`: validate `query` 10–300 chars after stripping; call `app.retrieval.search.search()` (reusing Feature 1's service, no retrieval logic duplicated per contracts/tools.md); format up to 3 hits as a fenced numbered listing of `doc_id#section` + text, or return the literal string `NO_RELEVANT_RUNBOOK`; never raise — validation failures return a string error (FR-005)
- [X] T017 [US1] Implement `app/agent/tools.py:lookup_tcode(args: dict) -> str`: validate `code` against `^[A-Z][A-Z0-9_/]{1,19}$` (Feature 1's `TCODE_RE`, reused); return the allow-list description or the literal string `unknown tcode`; never raise (FR-005)
- [X] T018 [US1] Implement `TOOLS = {"search_runbook": search_runbook, "lookup_tcode": lookup_tcode}` registry in `app/agent/tools.py`; a name not in `TOOLS` is never dispatched (Constitution IV allow-list requirement)
- [X] T019 [US1] Implement `app/agent/verify.py:verify_citations(result, evidence) -> TriageResult`: drop any `sources` entry whose `chunk_id` is not present in `evidence` (FR-009, R-06) — never raise, return the corrected result
- [X] T020 [US1] Implement `app/agent/verify.py:verify_tcodes(result, allow_list) -> TriageResult`: partition `tcodes` into verified (stay) and unverified (moved to `unverified_tcodes`, never dropped) against `data/tcodes.json` via Feature 1's `load_tcodes()` (FR-010, R-06)
- [X] T021 [US1] Implement `app/agent/fallback.py:build_fallback(evidence) -> TriageResult`: deterministic, no model call — `category` from the single best-scoring Evidence `Hit`'s runbook, `steps` from that runbook's `## Check` section (reusing Feature 1's `parse_runbook`-parsed sections), `tcodes`/`escalate_to` from that runbook's own front-matter, `sources` set to that one citation, `confidence="low"` (FR-008, R-05)
- [X] T022 [US1] Implement `app/agent/loop.py:gather_evidence(log, *, mode, max_steps) -> list[ToolCallRecord]`: Phase 1 per contracts/service.md — exposes `tools=` from the `TOOLS` registry (T018), dispatches via T016/T017, records each call as a `ToolCallRecord` (data-model.md § 3), appends `search_runbook` hits to Evidence; ends on natural stop (no tool call) in the `mode="agent"` case (US1's happy path; the `mode="E-ClassicRAG"` single-call and `mode="E-NoRAG"` no-call variants per R-08 are US4/T038)
- [X] T023 [US1] Implement `app/agent/formatter.py:format_result(evidence, log) -> TriageResult`: Phase 2 per contracts/service.md — one no-tools `app.llm.chat()` call asking for only a JSON object conforming to `TriageResult`, parsed via JSON extraction (fenced/prose-wrapped text tolerant) then `TriageResult.model_validate()` (happy-path branch; the repair loop around this call is T029)
- [X] T024 [US1] Implement `app/triage_service.py:triage(log, *, mode="agent", store=None) -> TriageResult`: validate length (reuses Feature 1's `InvalidQueryError` bounds) → normalize (reuses `app.normalize.*`, R-10) → `gather_evidence` (T022) → `format_result` (T023) → `verify_citations` (T019) → `verify_tcodes` (T020) — the single service entry point per contracts/service.md (the `out_of_scope`-forcing step is T027/US2; the repair/fallback wiring is T029/US3)
- [X] T025 [US1] Implement the `triage` subcommand in `app/cli.py` per contracts/cli.md: positional query or `--file`, `--json`, `--show-trace`; human output showing category/summary/tcodes/steps/escalate_to/sources/confidence; results to stdout, trace to stderr; exit codes 0/2/3/4/5
- [X] T026 [P] [US1] Extend `tests/test_cli_boundary.py` (or add `tests/test_triage_cli_boundary.py`) asserting `app/agent/*` and `app/triage_service.py` never import `app.cli` (Constitution VI, same rule Feature 1's T042 established)

**Checkpoint**: `python -m app.cli triage --file examples/tsv_dump.log` returns a cited, verified, allow-listed
result against the real gateway. **US1 independently testable.**

**Real findings from the live smoke test**: native tool-calling works reliably on `gemma-4-E4B-it` via the
course gateway — R-02's fallback protocol was not needed, resolving that open question. **A real bug was
caught and fixed**: `verify_tcodes` originally checked only the top-level `tcodes` list, leaving a fabricated
code in `Step.tcode` (the model put the *program name* `ZFI_MONTHLY_REPORT` there, not a T-code) unverified and
silently passed through — contradicting data-model.md § 1's own stated invariant that `Step.tcode` "must be a
key of `data/tcodes.json` by the time `verify_tcodes` has run." Fixed so `verify_tcodes` also sanitises every
`Step.tcode`, clearing an unverified one to `None` and recording it in `unverified_tcodes`
(`tests/test_agent_verify.py::test_verify_tcodes_also_sanitises_step_level_tcode`). Also observed: the model's
`sources` citations did not resolve to the evidence it was actually given on this run — `verify_citations`
correctly stripped them to an empty list rather than passing through an unverifiable claim. This is a real,
reportable model-quality finding (Constitution II), not a code defect, and belongs in US4's e2e
`unverified_claim_rate`/citation-resolution numbers, not papered over here.

---

## Phase 4: User Story 2 — An uncovered incident is refused, not guessed (Priority: P1)

**Goal**: When every retrieval call in a request finds nothing, the category is forced to `out_of_scope` in code,
regardless of what the model's own draft states.

**Independent Test**: Triage a log known to be out of the corpus's scope (a case Feature 1's eval set already
labels `out_of_scope`) and confirm the result's category is `out_of_scope` with zero T-codes and zero citations.

**Covers**: US2 acceptance scenarios 1–3.

### Tests for User Story 2

- [X] T027 [P] [US2] Write `tests/test_agent_verify.py::test_out_of_scope_forcing` (extends T012's file): with a mocked `format_result` returning a non-`out_of_scope` draft, if every `ToolCallRecord` with `tool == "search_runbook"` in Evidence returned `NO_RELEVANT_RUNBOOK`, the forced result has `category == "out_of_scope"`, `tcodes == []`, `sources == []` (FR-011, FR-012, R-07); a multi-search case where at least one call found something is **not** forced out of scope even if an earlier call found nothing (US2 acceptance scenario 3 / R-07's multi-search carve-out)

### Implementation for User Story 2

- [X] T028 [US2] Implement the `out_of_scope`-forcing step in `app/triage_service.py:triage()` per research.md R-07: after `gather_evidence` (T022), if Evidence is empty, skip `format_result` (T023) entirely and build the result directly with `category="out_of_scope"`, `tcodes=[]`, `sources=[]`, `confidence="low"` — no model call spent formatting a draft that would be discarded (contracts/service.md pipeline step 4)

**Checkpoint**: `python -m app.cli triage --file examples/hana_disk_full.log` returns `out_of_scope` with exit
code 0. **US1 + US2 both independently testable.**

---

## Phase 5: User Story 3 — Malformed output is repaired, then safely downgraded (Priority: P2)

**Goal**: Prove the repair loop and the fallback path — both already built as part of US1's `formatter.py` (T023)
and `fallback.py` (T021/T013), per the Ordering note — actually trigger correctly under a forced failure, and
that the system never crashes or returns an unvalidated result.

**Independent Test**: Force a validation failure (a mocked model response missing a required field) and confirm
a bounded number of repair attempts, then a fallback result that itself passes `TriageResult` validation with
reduced confidence.

**Covers**: US3 acceptance scenarios 1–3.

### Tests for User Story 3

- [ ] T029 [US3] Extend `tests/test_agent_formatter.py` (from T015) with the repair and fallback branches: a mocked `app.llm.chat` returning structurally invalid JSON on the first attempt, then valid JSON on retry, succeeds within the `REPAIR_ATTEMPTS` cap; a mock returning invalid JSON on every attempt exhausts the cap and routes to `app.agent.fallback.build_fallback()` (T021) rather than raising; the fallback result passes the same `TriageResult.model_validate()` every other result does (FR-006, FR-007, FR-008, SC-001)
- [ ] T030 [US3] Write `tests/test_agent_loop.py::test_max_steps_forces_stop` (extends T014's file): a mocked `app.llm.chat` that always returns a tool call (never stops on its own) is cut off after exactly `MAX_STEPS` dispatched calls, and the loop returns the evidence gathered so far rather than hanging (FR-003, SC-005)
- [ ] T031 [US3] Write `tests/test_agent_loop.py::test_repeated_call_guard` (extends T014's file): a mocked `app.llm.chat` that calls `search_runbook` with the same (normalized) query twice within one request results in exactly one dispatched call to T016; the second is answered from the already-recorded `ToolCallRecord` (FR-004, SC-006, research.md R-03)

### Implementation for User Story 3

- [ ] T032 [US3] Implement the repair loop in `app/agent/formatter.py:format_result()` (extends T023): on `TriageResult.model_validate()` failure, re-call `app.llm.chat()` with the invalid JSON and the validation error appended to the prompt, up to `REPAIR_ATTEMPTS = 2` (code constant per research.md R-04, not an env var) additional attempts; on exhaustion, call `app.agent.fallback.build_fallback(evidence)` (T021) instead of raising
- [ ] T033 [US3] Implement the `MAX_STEPS` bound and the repeated-call guard in `app/agent/loop.py:gather_evidence()` (extends T022): read `MAX_STEPS` from `app.config` (new accessor, same `_int()` pattern as `top_k()`); before dispatching, check `(tool, normalized_args)` — normalized via the same case-folding/whitespace-collapse Feature 1's `eval/schema.py` already uses (research.md R-03) — against this request's already-dispatched set; on the bound being reached, stop and return gathered Evidence rather than raising

**Checkpoint**: forcing a formatter failure never crashes `triage()` and never returns an invalid result; an
unbounded or repeating mock model is still terminated correctly. **US1–US3 all independently testable.**

---

## Phase 6: User Story 4 — One command reports end-to-end quality against named baselines (Priority: P2)

**Goal**: `eval/run_e2e.py` runs one configuration (the full agent, or a named baseline per research.md R-08)
over one split and writes a results file; `eval/run_all.py` runs all three as experiment E4 and reports category
accuracy, T-code recall, the unverified-claim rate, and the valid-output rate against the two named baselines.

**Independent Test**: Run the eval command and confirm it reports all four metrics for the full agent and both
named baselines, on the same 30 test cases, with the configuration (including baseline identity) recorded next
to each set of numbers.

**Covers**: US4 acceptance scenarios 1–4.

### Tests for User Story 4

- [ ] T034 [P] [US4] Write `tests/test_e2e_metrics.py` with hand-computed fixtures (mirrors Feature 1's `test_metrics.py` discipline): `category_accuracy`, `tcode_recall`, `unverified_claim_rate`, `valid_output_rate` each against a small fixed set of `CaseResult`-shaped inputs, including a case with `tcode_recall` between 0 and 1 and a case with `unverified_claim=True` from a non-empty `unverified_tcodes`
- [ ] T035 [P] [US4] Write `tests/test_triage_service.py::test_baselines_skip_evidence_gathering_not_verification` (research.md R-08): with `app.llm.chat` mocked, `mode="E-NoRAG"` never calls `gather_evidence`/any tool, and `mode="E-ClassicRAG"` calls `search_runbook` exactly once regardless of its result — but **both** still pass through `verify_citations`/`verify_tcodes` identically to `mode="agent"` (a baseline is not measured leniently)

### Implementation for User Story 4

- [ ] T036 [US4] Implement `app/triage_service.py:triage(..., mode=...)`'s `E-NoRAG`/`E-ClassicRAG` branches (extends T024) per contracts/service.md § Modes: `E-NoRAG` skips `gather_evidence` entirely and gives `format_result` the normalized log directly instead of Evidence; `E-ClassicRAG` calls `search_runbook` exactly once with the normalized log as the query, no loop
- [ ] T037 [US4] Implement the four e2e metric functions in `eval/run_e2e.py` per data-model.md § 5 and `docs/prepare/09_eval_plan.md` § 2: `category_accuracy` (predicted == gold, over all cases including OOS), `tcode_recall` (`|gold_tcodes ∩ tcodes| / |gold_tcodes|`, averaged over in-scope cases), `unverified_claim_rate` (fraction of cases with a dropped citation or a non-empty `unverified_tcodes`), `valid_output_rate` (fraction not requiring the fallback)
- [ ] T038 [US4] Implement `eval/run_e2e.py:run_config(split, mode, name) -> dict`: run one configuration over one split, write `eval/results/E4_{config_slug}_{split}.json` with the full `config` block (`corpus_sha`/`git_commit` copied from the loaded Feature-1 manifest, never recomputed — FR-019) plus per-case `CaseResult` entries, mirroring Feature 1's `eval/run_retrieval.py:run_config()` shape
- [ ] T039 [US4] Implement the E4 experiment in `eval/run_all.py`: run `agent`, `E-NoRAG`, `E-ClassicRAG` over the test split via T038, reusing Feature 1's `_assert_comparable` guard (same split/`corpus_sha` required across the three rows) (FR-016, FR-018)
- [ ] T040 [US4] Generate the E4 table into `eval/results/results.md` per contracts/file-formats.md § 5: each row stating which baseline (if any) it is, per-metric deltas, a verdict sentence per metric stated plainly whether or not the agent wins (FR-022), per-difficulty slices including Thai and mixed
- [ ] T041 [P] [US4] Write `tests/test_run_all_e4.py` asserting `eval/run_all.py`'s E4 step refuses to emit a comparison whose three rows disagree on `split` or `corpus_sha` (reusing Feature 1's `_assert_comparable`, now exercised with E4 inputs)

**Checkpoint**: `uv run python -m eval.run_all` produces E4 numbers for the agent and both baselines, written to
`eval/results/results.md`, reproducible via the chat cache. **US1–US4 all independently testable; US4 is the
measured-improvement claim this feature exists to prove.**

---

## Phase 7: User Story 5 — Every unverifiable claim is caught, not trusted (Priority: P3)

**Goal**: Prove — with tests specifically designed to force the failure, not just happy-path coverage — that a
fabricated citation or an out-of-allow-list T-code is always caught by `verify.py` (built in US1/T019–T020) and
never silently presented as verified, and that the e2e `unverified_claim_rate` metric (T037) actually reflects
this rather than being silently zero because such cases were discarded instead of counted.

**Independent Test**: Force the model to reference evidence it was never given (a citation never returned by
`search_runbook` during that run) and confirm the system strips it; similarly for a T-code outside the allow-list.

**Covers**: US5 acceptance scenarios 1–3.

### Tests for User Story 5

- [ ] T042 [P] [US5] Extend `tests/test_agent_verify.py` (from T012/T027) with `test_fabricated_citation_is_dropped`: a draft `TriageResult` whose `sources` includes a `chunk_id` never present in that request's Evidence has that entry removed by `verify_citations`, and the removal is observable (e.g. a returned flag or a shorter `sources` list), not just silently absorbed
- [ ] T043 [P] [US5] Extend `tests/test_agent_verify.py` with `test_out_of_allowlist_tcode_is_flagged_not_dropped`: a draft naming a T-code outside `data/tcodes.json` has it appear in `unverified_tcodes` and **not** in `tcodes` — confirm it is not simply deleted, since FR-016's hallucination rate depends on it being counted
- [ ] T044 [P] [US5] Write `tests/test_e2e_metrics.py::test_unverified_claim_rate_counts_dropped_and_flagged_claims` (extends T034): a `CaseResult` fixture whose `produced` has a non-empty `unverified_tcodes` or a citation-drop marker is counted by `unverified_claim_rate`; a clean fixture is not

**Checkpoint**: the `unverified_claim_rate` metric is proven, by test, to actually catch what it claims to catch
— not just assumed correct because `verify.py` exists. **All five user stories independently testable.**

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T045 Extend `README.md` with a Triage section: setup (none beyond Feature 1's), the `triage` command, an
  example run against `examples/tsv_dump.log`, the E4 result table, and agent-specific limitations (Constitution
  IX, FR-016)
- [ ] T046 [P] Walk `specs/002-triage-agent/quickstart.md` steps 0–8 on the current clone and fix any divergence
  between the documented and actual behaviour (Constitution IX) — same discipline as Feature 1's T081, including
  checking for any line-ending or caching surprises analogous to what Feature 1's walkthrough found
- [ ] T047 Commit `eval/results/E4_*.json` and the extended `results.md`/`failures.jsonl`, so every reported
  e2e number ships with the config that produced it (Constitution I)
- [ ] T048 Re-check this feature against Constitution I–X and record the outcome in
  `specs/002-triage-agent/plan.md` § Post-Design Re-Check, noting any principle the implementation strained —
  same discipline as Feature 1's T083
- [ ] T049 [P] Confirm `examples/tsv_dump.log`, `examples/hana_disk_full.log`, and `examples/mixed_lock_update.log`
  (already created by Feature 1) each produce the intended `triage` demo outcome (cited result, forced refusal,
  honestly-reported single-category limitation on the mixed log per SC-010) — no new example files needed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies
- **Foundational (Phase 2)**: depends on Setup — **blocks every user story**
- **US1 (Phase 3)**: depends on Foundational
- **US2 (Phase 4)**: depends on US1 (extends `triage_service.py`'s pipeline built in T024)
- **US3 (Phase 5)**: depends on US1 (tests/extends the repair loop and loop bound built in T022/T023)
- **US4 (Phase 6)**: depends on US2 and US3 (the baselines and metrics need the full pipeline, including
  `out_of_scope` forcing and the repair/fallback path, to be measured honestly)
- **US5 (Phase 7)**: depends on US1 (tests/extends `verify.py` built in T019–T020) and benefits from US4's
  metric functions existing (T044) to prove the metric, not just the mechanism
- **Polish (Phase 8)**: depends on all desired stories

### Deviation from the template's parallel-stories model

As in Feature 1, these stories are not mutually independent, and the plan does not pretend otherwise. US2–US5
all extend modules US1 builds. What each story *does* preserve is the template's real requirement — an
independently **testable** increment with a checkpoint that can be validated on its own, confirmed above for
every phase.

### Within Each User Story

- Tests are written first and must fail before the implementation tasks in the same phase
- Schema before tools/verify/fallback; tools/verify/fallback before loop/formatter (mocked-model tests); those
  before `triage_service.py`; that before the CLI edge
- Commit after each task or logical group — small, incremental commits (Constitution IX)

### Parallel Opportunities

- T001 + T002 (Setup)
- T003 + T006 (schema definition + its test can be drafted in parallel, though T006 must fail before T003–T005
  land); T008 + T010 alongside T007/T009
- **T011–T015** — all five US1 test files are independent and the largest parallel block in this feature
- T026 (CLI boundary test) is independent of T016–T025's implementation order
- T027 (independent of T011–T015's files); T034 + T035 (US4 tests); T042 + T043 + T044 (US5 tests)
- T041, T046, T048, T049 are independent checks

---

## Parallel Example: User Story 1 tests

```bash
# All five US1 test files touch disjoint source files and can be written in parallel:
Task: "Write tests/test_agent_tools.py per contracts/tools.md"
Task: "Write tests/test_agent_verify.py (happy-path branches)"
Task: "Write tests/test_agent_fallback.py"
Task: "Write tests/test_agent_loop.py (happy-path branches)"
Task: "Write tests/test_agent_formatter.py (happy-path branch)"
```

## Parallel Example: User Story 5 tests

```bash
Task: "Extend tests/test_agent_verify.py with test_fabricated_citation_is_dropped"
Task: "Extend tests/test_agent_verify.py with test_out_of_allowlist_tcode_is_flagged_not_dropped"
Task: "Write tests/test_e2e_metrics.py::test_unverified_claim_rate_counts_dropped_and_flagged_claims"
```

---

## Implementation Strategy

### MVP scope

The honest MVP is **US1 + US2: a trustworthy triage result, including the refusal case** (through T028). A
pipeline that only ever answers and never refuses is not the system the spec describes — User Story 2 is P1 for
exactly that reason (Constitution III: refusing correctly is as important as answering correctly).

If time collapses further, the defensible stopping point is **T026** (end of US1 alone): a cited, verified,
allow-list-checked happy-path result, honestly incomplete (no `out_of_scope` forcing yet) rather than silently
guessing on uncovered logs — but this should be treated as a true fallback position, not the target.

### Incremental delivery

1. Setup + Foundational → schema and chat seam exist, unit-tested, no agent logic yet
2. US1 → a verified, cited result for a known in-scope log · the MVP core
3. US2 → uncovered incidents are refused, not guessed · **completes the honest MVP**
4. US3 → malformed output never crashes or escapes validation (proves what US1 already built)
5. US4 → the measured end-to-end comparison this feature exists to produce · **SC-007, SC-008**
6. US5 → the verification guarantee is proven by test, not just assumed · **SC-002, SC-003 made checkable**
7. Polish → README, quickstart rehearsal, committed e2e results, constitution re-check

### Single-author note

As in Feature 1, the template's parallel-team strategy does not apply — one maintainer. The `[P]` markers are
about *safe reordering* (disjoint files, no incomplete dependencies), most useful in the T011–T015 US1 test
block where writing all five failing tests can be interleaved with reading the relevant contract sections.

---

## Notes

- 49 tasks: 2 Setup, 8 Foundational, 16 US1, 2 US2, 5 US3, 8 US4, 3 US5, 5 Polish
- `[P]` = disjoint files, no dependency on an incomplete task
- Field constraints are quoted verbatim from data-model.md so no rule is left to implementation-time discretion
- Verify each phase's tests fail before implementing that phase
- Stop at any checkpoint to validate the increment independently
