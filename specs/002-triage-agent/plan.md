# Implementation Plan: Triage Agent — Bounded Tool-Calling Loop with Verified Structured Output

**Branch**: `002-triage-agent` | **Date**: 2026-11-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-triage-agent/spec.md`

## Summary

Build the triage agent on top of Feature 1's already-committed `search()` service and corpus: an explicit,
framework-free tool-calling loop (`search_runbook`, `lookup_tcode`) bounded by `MAX_STEPS` and a repeated-call
guard, followed by a no-tools formatter call that produces a structured `TriageResult`, validated against a
schema and a capped repair loop, with every citation and T-code verified by code against actual evidence rather
than trusted from the model. When retrieval finds nothing, the category is forced to `out_of_scope` in code, not
asked of the model. A single eval command reports four end-to-end metrics (category accuracy, T-code recall,
hallucination rate, valid-output rate) against two named baselines (no-retrieval, single-call non-agentic
retrieval), on the same 40 labelled cases Feature 1 already committed — no new eval set is authored.

Technical approach: one new service module, `app/triage_service.py`, orchestrating a small `app/agent/` package
(`tools.py` the read-only allow-listed tool registry, `loop.py` the bounded evidence-gathering loop, `formatter.py`
the JSON-extraction-and-repair phase, `verify.py` the citation/T-code/`out_of_scope` post-check, `fallback.py` the
deterministic downgrade). `app/llm.py` gains a second function, `chat(messages, tools=None, temperature=0)`,
alongside its existing `embed()` — still the only module that calls the gateway (Constitution VI). A disk cache
for chat completions, content-addressed like Feature 1's embedding cache, makes repeated eval runs both free and
reproducible. `eval/run_e2e.py` runs one configuration (the full agent, or a named baseline) over one split and
writes a results file in the same shape as Feature 1's `eval/run_retrieval.py`; `eval/run_all.py` is extended to
run the E4 comparison and append its table to `results.md`.

## Technical Context

**Language/Version**: Python 3.12 (unchanged from Feature 1; same `pyproject.toml`)

**Primary Dependencies**: `openai>=1.40` (chat completions via the same class-proxy client Feature 1 already
constructs for embeddings), `pydantic>=2.7` (the new `TriageResult`/`Step` schemas). No new dependency is added —
`app/llm.py`, `app/schemas.py`, `app/retrieval/search.py`, `app/retrieval/runbooks.py` (for the T-code allow-list),
and `app/normalize.py` are all reused as-is from Feature 1.

**Explicitly not used**: any LLM orchestration framework (LangChain/LlamaIndex) — the agent loop is explicit
project code (Constitution V); any second LLM provider; any new vector/database dependency.

**Storage**: plain files, extending Feature 1's layout. New: `data/chat_cache/` (chat-completion cache,
git-ignored, same shape as `data/cache/`'s embedding cache) and `eval/results/` gains e2e result files
(`E4_*.json`) and an extended `failures.jsonl` (agent-specific failure types added to Feature 1's taxonomy).
Nothing in Feature 1's committed files changes.

**Testing**: `pytest`, fully offline — `app.llm.chat` mocked at the same single seam `app.llm.embed` already is
(Constitution VIII). Agent behaviour (loop bound, repeated-call guard, repair cap, verification, fallback) is
unit-tested with the model mocked; end-to-end answer *quality* is measured only by `eval/run_e2e.py`, never
asserted in a unit test (same discipline as Feature 1's retrieval quality).

**Target Platform**: local developer machine (Windows 11 for the author), unchanged from Feature 1.

**Project Type**: single Python package, extending Feature 1's CLI edge with a `triage` subcommand. No API, no UI
— those are Feature 3.

**Performance Goals**: not a measured success criterion for this feature (unlike Feature 1's SC-013 search
latency) — gateway round-trip latency for `MAX_STEPS` tool-calling turns plus the formatter call dominates and is
outside this project's control. The chat cache (R-09) keeps repeated eval runs free of that latency entirely.

**Constraints**: the LLM is called from exactly one module (`app/llm.py`, Constitution VI); every evaluated or
flow-controlling chat call uses `temperature=0` (Constitution IV); every tool is read-only and allow-listed, with
arguments validated before execution; the evidence-gathering loop is bounded by `MAX_STEPS` (already reserved in
`.env.example`, unused until this feature) and a repeated-call guard; the system must never crash on model output
and must never return a response that fails its own schema.

**Scale/Scope**: the same 16-runbook corpus and 40-case eval set as Feature 1 (10 dev, 30 test) — no new corpus
content. One triage request issues at most `MAX_STEPS` tool calls plus one formatter call plus up to 2 repair
calls; a full E4 run over the 30 test cases is 3 configurations (agent, E-NoRAG, E-ClassicRAG) x 30 cases, cached
after the first pass.

### Decisions carried in from the spec

The spec's Assumptions section already resolves what would otherwise be planning ambiguities: step bound and
repair-attempt count are configuration/constants decided here (not re-litigated — see research.md R-04); the
tool-calling mechanism (native vs. a text-based fallback protocol) is a planning-phase choice (R-02); no new eval
cases are authored (FR-017's letter is satisfied by Feature 1's existing `gold_tcodes` field, confirmed present in
`eval/schema.py`'s `EvalCase`). No `NEEDS CLARIFICATION` markers remain in this Technical Context.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution v1.0.0. Gate status: **PASS** (initial), **PASS** (re-checked post-Phase 1 — see
[Post-Design Re-Check](#post-design-re-check)).

| Principle | How this plan satisfies it | Gate |
|---|---|---|
| **I. Evaluation-First** | No new eval set is authored — Feature 1's committed `cases_dev.jsonl`/`cases_test.jsonl` already carry `gold_tcodes`, satisfying what this feature's end-to-end metrics need (FR-017). The four end-to-end metric *functions* and the two named baselines (E-NoRAG, E-ClassicRAG) are written and unit-tested before the agent loop is wired into `eval/run_e2e.py` for real, mirroring Feature 1's R-12 task-ordering discipline. `MAX_STEPS`/repair-cap tuning (if any) uses dev cases only; test cases are reporting-only, enforced the same way Feature 1's `sweep_min_score` enforces it (a guarded function, tested). | PASS |
| **II. Honest Reporting** | Every wrong, fallback, or unverified-claim case is written to `eval/results/failures.jsonl`, extending Feature 1's failure taxonomy with agent-specific types (FR-021). The report states plainly whether the agent beats each named baseline on each metric, including when it does not (FR-022, mirroring Feature 1's verdict sentence). Synthetic cases are already flagged by Feature 1; Limitations carries forward and gains agent-specific items (model size/tool-calling reliability, mixed-case single-category limitation). | PASS |
| **III. Grounded Answers Only** | Every citation is verified against the evidence actually retrieved during that request (FR-009) before the response is returned — never trusted from the model's own text. T-codes are verified against Feature 1's allow-list (FR-010); an unverified one is recorded, never presented as verified. When every retrieval call returns nothing, `out_of_scope` is forced in code (FR-011), not asked of the model. | PASS |
| **IV. Untrusted Model and Inputs** | `TriageResult`/`Step` are Pydantic v2 models with semantic checks beyond structural validation (citations exist in evidence, T-codes allow-listed). Invalid output goes through a capped repair loop (FR-007), then a deterministic fallback (FR-008) — the system never crashes and never returns a response that fails its own schema (SC-001). The pasted log is delimited and treated as data throughout (FR-014) — the same prompt-injection posture Feature 1's constitution compliance check already names. Tools are read-only, allow-listed, with arguments validated before execution (Constitution IV literal text) — `search_runbook` and `lookup_tcode` call only Feature 1's existing read-only `search()`/`load_tcodes()`. The loop is bounded by `MAX_STEPS` and a repeated-call guard (FR-003, FR-004). `temperature=0` on every evaluated or flow-controlling call (both agent-loop and formatter calls). | PASS |
| **V. Course Constraints** | Chat calls go through the same `OpenAI()` client construction site Feature 1 already uses for embeddings, in `app/llm.py` — chat model `gemma-4-E4B-it` (the `CHAT_MODEL` env var Feature 1's `.env.example` already reserved but left unconsumed). No orchestration framework; the loop is explicit project code per `app/agent/loop.py`. Differentiator from the course reference app: this feature adds the agentic tool-calling loop and verified structured output on top of Feature 1's own hybrid-retrieval differentiator. | PASS |
| **VI. Layered, Simple Architecture** | `app/triage_service.py` is the single service entry point (`triage(log) -> TriageResult`), called identically by the CLI's new `triage` subcommand and by `eval/run_e2e.py` — the same single-service-path discipline Feature 1's `search()` established (research.md R-07 in Feature 1). `app/agent/*` is repository-adjacent orchestration, not an edge. `app/llm.py` remains the only module that constructs a client or calls the gateway — `chat()` is added beside the existing `embed()`, not a second call site. No vector database, no new infrastructure. | PASS |
| **VII. Scope Discipline** | This is step 3 of the constitutional build order (`eval set -> retrieval -> agent + structured output -> CLI -> API -> web UI -> polish`); steps 1–2 (Feature 1) already passed their compliance checks and committed. This feature explicitly excludes any HTTP API, SSE, or web UI (Feature 3's responsibility, per spec Out of Scope), any real SAP connection or fix execution, and multi-turn conversation — all named in the spec's own Out of Scope section, matching Constitution VII's v1 exclusions verbatim. | PASS |
| **VIII. Testing** | Deterministic components get offline unit tests with `app.llm.chat` mocked: tool-argument validation, the repeated-call guard, `MAX_STEPS` termination, JSON extraction, the repair loop (including cap exhaustion), citation verification, T-code allow-list verification, the `out_of_scope`-forcing rule, and the deterministic fallback construction. The four end-to-end metric functions get hand-computed-fixture tests, same discipline as Feature 1's `eval/metrics.py`. Answer *quality* (is this specific triage actually good) is measured only by `eval/run_e2e.py`, never asserted in a unit test. | PASS |
| **IX. Runnable from README, Incremental History** | README gains a `triage` section (setup already done by Feature 1's README) with a runnable example and the e2e result table, reproducible via one documented command, consistent with Feature 1's quickstart-rehearsal discipline (T081-equivalent task planned here too). Commits land per user-story phase, small and incremental, as Feature 1's did. | PASS |
| **X. Content and Licensing** | No new runbook content and no UI in this feature, so no new licensing or branding surface is introduced. The formatter prompt and fallback logic cite only `runbook-id#section` addresses already governed by Feature 1's Constitution X compliance. | PASS |

**Initial gate result: PASS — no unjustified violations.** Two additions beyond "the simplest thing that works"
are recorded in [Complexity Tracking](#complexity-tracking) with their justification.

## Project Structure

### Documentation (this feature)

```text
specs/002-triage-agent/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output — resolved design decisions
├── data-model.md         # Phase 1 output — entities, schemas, validation rules
├── quickstart.md         # Phase 1 output — runnable validation walkthrough
├── contracts/            # Phase 1 output
│   ├── service.md         #   triage() service contract
│   ├── tools.md           #   search_runbook / lookup_tcode tool contracts
│   ├── cli.md             #   `triage` subcommand contract
│   └── file-formats.md    #   TriageResult, chat-cache, e2e results, failures schemas
├── checklists/
│   └── requirements.md    # Spec quality checklist (from /speckit-specify)
└── tasks.md               # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
app/
├── llm.py                # EXTEND: add chat(messages, tools=None, temperature=0) beside existing embed()
├── schemas.py             # EXTEND: add TriageResult, Step (Pydantic)
├── cli.py                 # EXTEND: `triage` subcommand — parse + print only
├── triage_service.py      # NEW — SERVICE: triage(log, *, store=None) -> TriageResult
└── agent/
    ├── __init__.py
    ├── tools.py            # read-only allow-listed tool registry: search_runbook, lookup_tcode
    ├── loop.py             # Phase 1: bounded evidence-gathering loop, repeated-call guard
    ├── formatter.py        # Phase 2: JSON extraction, Pydantic validation, capped repair loop
    ├── verify.py           # post-check: citation verification, T-code allow-list, out_of_scope forcing
    └── fallback.py         # deterministic downgrade from the top-1 retrieved runbook

data/
└── chat_cache/             # NEW, GENERATED, git-ignored: chat-completion cache by sha256(model|temp|messages|tools)

eval/
├── run_e2e.py              # NEW — one configuration (agent or a named baseline) over one split -> e2e results json
├── run_all.py              # EXTEND: E4 comparison (agent vs E-NoRAG vs E-ClassicRAG) appended to results.md
└── results/                 # COMMITTED: E4_*.json, results.md extended, failures.jsonl extended

tests/
├── test_llm_chat_cache.py  # chat() cache behaviour, mirrors test_llm_cache.py's embed() coverage
├── test_agent_tools.py     # tool-argument validation, allow-list
├── test_agent_loop.py      # MAX_STEPS termination, repeated-call guard, natural stop
├── test_agent_formatter.py # JSON extraction, repair loop including cap exhaustion
├── test_agent_verify.py    # citation verification, T-code allow-list, out_of_scope forcing
├── test_agent_fallback.py  # deterministic fallback construction and its own schema validity
├── test_triage_service.py  # end-to-end wiring with the model mocked
├── test_e2e_metrics.py     # the four e2e metric functions, hand-computed fixtures
└── test_triage_cli_boundary.py  # app/agent/ and app/triage_service.py never import app.cli
```

### Structure Decision

Extends Feature 1's single-package, three-layer structure (Constitution VI) rather than introducing a parallel
one. `app/triage_service.py` plays the same "single service, two callers" role for the CLI and eval harness that
`app/retrieval/search.py` already plays for Feature 1 — this is deliberate: it is the pattern Feature 1's own
research.md (R-07) established specifically so the measured system and the demonstrated system can never diverge,
and there is no reason to invent a second pattern here. `app/agent/` sits beside `app/retrieval/` as
repository-adjacent orchestration; `app/llm.py` gains a second function rather than a second module, keeping
Constitution VI's "LLM called from exactly one module" literally true. This matches the target repo layout
already sketched in `docs/prepare/03_tech_stack.md` § 4 (`app/agent/{tools,loop,formatter}.py`,
`app/triage_service.py`) — followed here rather than re-derived, since the author already designed it before this
spec was written.

## Complexity Tracking

> Two items exceed "the simplest thing that works" (Constitution VI). Each is required by another principle, so
> neither is an unjustified violation — but both are recorded here.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| A disk cache for chat completions (`data/chat_cache/`), beyond the embedding cache Feature 1 already has | FR-020 requires two consecutive end-to-end evaluation runs to yield identical verification-level outcomes. A full E4 run calls the chat model up to `MAX_STEPS + 3` times per case across 3 configurations x 30 test cases — re-calling the gateway on every run makes identical-outcome claims depend on upstream determinism this project does not control, and costs real latency/quota on every repeat. | Re-calling the gateway each run: cheapest to build, but FR-020 becomes an untestable hope rather than a guarantee, and reruns during development become slow and quota-expensive — the exact problem Feature 1's R-09 embedding cache already solved for the same reason. |
| Two-phase model interaction (tool-calling loop, then a separate no-tools formatter call) rather than one call that both reasons and emits structured JSON | `docs/prepare/02_design.md` § 5.3 and the course material it cites (L10 p.8) record that asking a model to emit "ONLY JSON" in the same call that also exposes `tools=` suppresses native tool-calling on the course's chat model. Splitting into Phase 1 (evidence-gathering, tools exposed) and Phase 2 (formatting, no tools) is what makes both native tool-calling and reliable JSON output achievable at all. | One combined call: simpler code, but empirically breaks tool-calling on the course gateway's model per the author's own prior testing notes — not a hypothetical risk being guarded against speculatively. |

## Phase 0 — Research

See [research.md](./research.md) for the full decision log (twelve entries, each with rationale and rejected
alternatives). The four that most affect implementation:

- **R-02** Tool-calling mechanism: native function calling is the default; a text-based fallback protocol is
  planned but built behind the same tool-dispatch interface, activated only if native calling proves unreliable
  during early smoke-testing (the course's own documented risk, `docs/prepare/00_START_HERE.md` item 2).
- **R-04** `MAX_STEPS=5` (env var, already reserved) and a repair cap of 2 attempts (code constant, not an env
  var — a correctness bound, not a deployment knob, matching Feature 1's treatment of its own experiment matrix
  as code rather than configuration).
- **R-07** The `out_of_scope`-forcing rule is evaluated after the evidence-gathering loop ends: if every
  `search_runbook` call in the request returned no relevant result, the category is overwritten to `out_of_scope`
  regardless of the model's own text, before the formatter phase even runs.
- **R-09** Chat completions are cached on disk, content-addressed (`sha256(model|temperature|messages|tools)`),
  mirroring Feature 1's embedding cache — the mechanism behind FR-020's reproducibility guarantee.

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md) — `TriageResult`, `Step`, `ToolCallRecord`, `UnverifiedTcode`, the e2e
  `RunResult`/`Comparison`/`FailureRecord` extensions, each validation rule traced to its FR.
- [contracts/service.md](./contracts/service.md) — `triage()` signature, pipeline, guarantees, error behaviour.
- [contracts/tools.md](./contracts/tools.md) — `search_runbook`/`lookup_tcode` argument contracts, return shapes,
  the allow-list and read-only guarantees.
- [contracts/cli.md](./contracts/cli.md) — the `triage` subcommand surface, exit codes, output shape.
- [contracts/file-formats.md](./contracts/file-formats.md) — `TriageResult` JSON shape, chat-cache entry shape,
  e2e results json, extended `failures.jsonl` shape.
- [quickstart.md](./quickstart.md) — the runnable validation path, each step mapped to the success criterion it
  demonstrates.

### Post-Design Re-Check

Re-evaluated after writing the Phase 1 artifacts. Still **PASS** on all ten principles. One point the design work
changed:

1. **Principle III gained a second mechanical guard.** Defining `verify.py`'s contract in
   [contracts/service.md](./contracts/service.md) exposed that citation verification and T-code verification are
   two independent checks with different failure modes (a citation either resolves or is dropped; a T-code either
   verifies or moves to `unverified_tcodes` — it is never dropped, since naming an unrecognised code is itself a
   reportable finding, not noise to hide). Keeping them as two named functions rather than one combined "sanitize"
   step is what makes each independently unit-testable per Constitution VIII.

No new Complexity Tracking entries arose from Phase 1.
