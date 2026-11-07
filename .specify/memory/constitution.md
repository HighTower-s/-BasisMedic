<!--
SYNC IMPACT REPORT (scratch — remove before committing the amended constitution)

Version change: none (unfilled template scaffold) -> 1.0.0
Bump rationale: Initial ratification. No prior ratified version existed; the file contained only
unreplaced placeholder tokens.

Modified principles:
- [PRINCIPLE_1_NAME] -> I. Evaluation-First (NON-NEGOTIABLE)
- [PRINCIPLE_2_NAME] -> II. Honest Reporting
- [PRINCIPLE_3_NAME] -> III. Grounded Answers Only
- [PRINCIPLE_4_NAME] -> IV. Treat the Model and All Inputs as Untrusted
- [PRINCIPLE_5_NAME] -> V. Course Constraints

Added sections:
- VI. Layered, Simple Architecture
- VII. Scope Discipline - Small and Finished Beats Big and Broken
- VIII. Testing
- IX. Runnable from README, Incremental History
- X. Content and Licensing
- Additional Constraints: Technology Stack and Fixed Defaults (filled [SECTION_2_NAME])
- Development Workflow and Quality Gates (filled [SECTION_3_NAME])

Removed sections: none

Follow-up TODOs: none. All placeholder tokens replaced; no deferred fields.
-->

# BasisMedic Constitution

BasisMedic is an evaluated RAG + tool-calling agent that triages SAP Basis incidents. A user pastes
an SAP error log or short dump; the system returns the incident category, the T-codes to open in
order, step-by-step checks, and citations to the runbook sections used. Its users are junior SAP
Basis admins and on-call staff, who will act on its output under time pressure. It is a university
capstone project for the course *Building LLM-Powered Applications*.

## Core Principles

### I. Evaluation-First (NON-NEGOTIABLE)

- The labelled eval set (10 dev cases + 30 test cases) MUST be written and committed BEFORE any
  retrieval or agent code is written.
- Every retrieval or prompt change MUST be measured against a named baseline. The required
  baselines are: BM25-only; dense retrieval with naive fixed-size chunks; LLM with no retrieval.
- Exactly one variable MUST change per measured experiment. Bundled changes are not an acceptable
  result.
- Tuning decisions (e.g. `min_score`, chunk strategy, top-k, prompt wording) MUST use the dev set
  only. The test set is for reporting only and MUST NOT inform any tuning decision.
- Every reported result MUST be reproducible from the repository with one command, and MUST be
  committed together with the exact config that produced it.

**Rationale**: Without a frozen eval set written first, "improvement" degenerates into whatever
looks better in the last demo, and the test set silently becomes a second dev set. Writing the eval
first also forces the problem to be defined before the machinery.

**Compliance check**: Git history shows the eval set committed before `retrieval/` and `agent/`
code. The repository contains a single documented command that regenerates every reported number.
Each results artifact carries its config (model, embedding model, chunk strategy, `min_score`,
top-k, prompt version) and the baseline it is compared against. Any PR changing retrieval or prompts
includes before/after dev-set numbers for one changed variable. No commit shows test-set numbers
being used to choose a parameter.

### II. Honest Reporting

- Numbers MUST NOT be inflated, rounded favourably, cherry-picked, or invented.
- Failure cases MUST be recorded in a failures log and MUST appear in the written report and the
  live demo.
- Synthetic data MUST be labelled as synthetic wherever it is used or reported.
- Limitations MUST be stated explicitly, including corpus size, domain coverage gaps, and known
  failure modes.

**Rationale**: The project's value is the evidence it produces, not the score it claims. An honest
weak result is a usable result; an inflated one is worthless and, for on-call users acting on
triage output, actively dangerous.

**Compliance check**: A failures log exists in the repository and is referenced by the report and
the demo script. Every reported metric traces to a committed results artifact produced by the
reproduction command. Synthetic cases are flagged in the eval set itself. The report contains an
explicit Limitations section.

### III. Grounded Answers Only

- Answers MUST be derived only from the project's own runbook corpus. No outside knowledge, no
  model recall.
- Every answer MUST cite `runbook#section` ids.
- Citations MUST be verified by code against the evidence actually returned by the tools. T-codes
  MUST be verified against a T-code allow-list. Neither is ever trusted from the model.
- If nothing passes the relevance floor (`min_score`), the system MUST return `out_of_scope` and
  MUST NOT ask the LLM to guess.

**Rationale**: A plausible-sounding but ungrounded T-code sequence is the worst possible output for
an on-call admin: it is actionable and wrong. Verification in code — not in the prompt — is the only
guarantee that survives a model that has decided to be creative.

**Compliance check**: Unit tests assert that an answer whose citations are not present in the
returned evidence is rejected, that a T-code outside the allow-list is rejected, and that an empty
or below-floor retrieval result yields `out_of_scope` with zero LLM calls. No code path constructs
an answer from model text without passing it through the citation and T-code verifiers.

### IV. Treat the Model and All Inputs as Untrusted

- All LLM output MUST be parsed and validated against Pydantic schemas plus semantic checks
  (citations exist, T-codes allow-listed, required fields non-empty).
- Invalid output MUST go through a repair loop with a hard cap, then fall back to a deterministic
  response. The system MUST never crash on model output and MUST never emit invalid JSON to a
  caller.
- User-pasted logs and tool results MUST be delimited and treated as data, never as instructions.
- Tool calls MUST be allow-listed, their arguments validated before execution, and all tools MUST
  be read-only.
- Every agent loop MUST be bounded by a maximum step count and a repeated-call guard.
- `temperature=0` is REQUIRED for any call that is evaluated or that controls flow.

**Rationale**: The model is a probabilistic component inside a deterministic system, and a pasted
SAP short dump is attacker-controlled text as far as the prompt is concerned. Bounding and
validating at the boundary is what makes the rest of the system reasonable to reason about.

**Compliance check**: Unit tests with the LLM mocked cover malformed JSON, JSON wrapped in prose,
schema-valid-but-semantically-invalid output, repair-cap exhaustion reaching the deterministic
fallback, a disallowed tool name, invalid tool arguments, max-step termination, and repeated-call
termination. A grep of LLM call sites shows `temperature=0` on every evaluated or flow-controlling
call. Prompt templates show explicit delimiters around user logs and tool results.

### V. Course Constraints

- All chat and embedding calls MUST go through the class proxy via the OpenAI SDK (`OpenAI()`),
  using chat model `gemma-4-E4B-it` and embedding model `bge-m3`. No other LLM provider may be
  used.
- Configuration MUST come from environment variables. Secrets MUST NEVER be committed to the
  repository, in any form, at any time.
- The project MUST clearly differ from the course reference application: its own domain corpus, its
  own eval set, hybrid retrieval, and structured triage output.
- LLM orchestration frameworks (LangChain, LlamaIndex, or equivalents) MUST NOT be used. The agent
  loop MUST be written explicitly in project code.

**Rationale**: These are the assessment's hard boundaries. A framework would also hide exactly the
agent-loop mechanics the course is meant to demonstrate, and hiding them removes the project's
main technical contribution.

**Compliance check**: Dependency manifest contains no orchestration framework. A grep shows one
client construction site and no provider SDK other than `openai`. `.env.example` is committed with
placeholder values; `.env` is git-ignored; history contains no secret material. The report names the
four concrete differences from the reference app.

### VI. Layered, Simple Architecture

- Layering MUST be edge (CLI, FastAPI router, web UI) -> service (triage orchestration) ->
  repository (index, runbooks, T-code list). Dependencies point inward only.
- Edges MUST contain no business logic.
- The LLM MUST be called from exactly one module.
- The CLI MUST always work, including after the web UI exists, as the fallback for live demos.
- The core and the eval MUST NEVER depend on the web UI.
- The simplest implementation that works is REQUIRED — for example brute-force numpy search at this
  corpus size, not a vector database.

**Rationale**: One LLM call site makes `temperature=0`, retries, and logging enforceable in one
place. A CLI that cannot break when the UI breaks is what makes a live demo survivable. At this
corpus size, infrastructure is cost without benefit.

**Compliance check**: Imports confirm no inward dependency from service or repository to any edge,
and no import of web-UI code from core or eval. A grep finds exactly one module constructing or
calling the LLM client. The eval command runs with the web UI absent. The README documents the CLI
demo path.

### VII. Scope Discipline — Small and Finished Beats Big and Broken

- Build order is fixed: eval set -> retrieval -> agent + structured output -> CLI -> API -> web UI
  -> polish.
- A lower-priority item MUST NOT start until all higher-priority items pass their own compliance
  checks.
- Out of scope for v1: connecting to real SAP systems; executing fixes; multi-turn follow-up
  conversations.

**Rationale**: A capstone is graded on what demonstrably works. Starting the web UI before retrieval
is measured is the standard way these projects end up with a beautiful shell around an unevaluated
core.

**Compliance check**: Every plan and task list orders work by this priority chain and states which
gate the previous stage passed. Any task touching a real SAP connection, fix execution, or
multi-turn state is rejected as out of scope for v1.

### VIII. Testing

- Deterministic components MUST have unit tests with the LLM mocked: tool validation, JSON
  extraction and repair, metrics computation, normalization, API status codes (422, 502, 504), and
  SSE frame format.
- Answer quality MUST be measured by the eval harness, not asserted in unit tests.

**Rationale**: Unit tests are for the parts whose correct behaviour is knowable in advance.
Pinning answer wording in assertions produces brittle tests that measure the prompt rather than the
system, which is what the eval set exists for.

**Compliance check**: The test suite runs without network access or API credentials. Each listed
deterministic component has named tests. No unit test asserts on generated prose content.

### IX. Runnable from README, Incremental History

- A newcomer MUST be able to clone the repository, configure `.env`, ingest the corpus, run the
  system, and reproduce the reported eval numbers by following the README alone.
- Commits MUST be small and incremental and MUST show real progress. Squashing the project into a
  few large commits is not acceptable.

**Rationale**: Reproducibility by a stranger is the practical test of whether the work is real. The
commit history is also part of what is assessed, and it is the only record of how the result was
reached.

**Compliance check**: The README path is walked end-to-end on a clean clone before submission, and
the reproduced numbers match the committed results. `git log` shows incremental commits mapping to
the build order in Principle VII.

### X. Content and Licensing

- Runbooks MUST be written in our own words, in English, summarising public SAP documentation.
- Each runbook MUST carry a References section of source URLs.
- SAP Notes and long passages of SAP documentation MUST NOT be copied.
- Third-party logos or branding (e.g. Gemini, ChatGPT, Claude) MUST NOT appear in the UI.

**Rationale**: The corpus is the project's own contribution and must be ours to distribute.
Borrowed branding also misrepresents who built the system.

**Compliance check**: Every runbook file has a References section with at least one URL. Review
confirms no verbatim passages from SAP documentation. UI assets contain no third-party logos.

## Additional Constraints: Technology Stack and Fixed Defaults

These are consequences of the principles above, recorded here so they are not re-litigated per
feature:

- **LLM access**: OpenAI SDK (`OpenAI()`) against the class proxy. Chat model `gemma-4-E4B-it`;
  embeddings `bge-m3`. One call site (Principle VI); `temperature=0` where evaluated or
  flow-controlling (Principle IV).
- **Retrieval**: hybrid (lexical BM25 + dense `bge-m3`), brute-force numpy similarity search. A
  relevance floor `min_score` gates every answer; below it the result is `out_of_scope`.
- **Structured output**: Pydantic schemas define the triage result — category, ordered T-codes,
  step-by-step checks, `runbook#section` citations — validated plus semantically checked, with a
  capped repair loop and a deterministic fallback.
- **Tools**: read-only, allow-listed, arguments validated before execution.
- **Edges**: CLI (always available), FastAPI router (422 on invalid input, 502 on upstream failure,
  504 on timeout, SSE for streaming), optional web UI last.
- **Configuration**: environment variables only; `.env.example` committed, `.env` git-ignored.
- **Not used**: LangChain, LlamaIndex, or any other LLM orchestration framework; any non-proxy LLM
  provider; any vector database.

## Development Workflow and Quality Gates

- Work proceeds in the Principle VII order. Each stage has an explicit gate that MUST pass before
  the next stage starts:
  1. **Eval set** — 10 dev + 30 test cases committed, synthetic cases labelled.
  2. **Retrieval** — dev-set numbers against all three named baselines, committed with config.
  3. **Agent + structured output** — schema validation, repair cap, deterministic fallback, bounded
     loop, citation and T-code verification all unit-tested with the LLM mocked.
  4. **CLI** — reproduces the eval command and serves as the demo fallback.
  5. **API** — 422/502/504 and SSE frame format unit-tested.
  6. **Web UI** — no business logic, no third-party branding, core and eval independent of it.
  7. **Polish** — README walked on a clean clone; report with failures log and limitations.
- Every change to retrieval or prompts changes one variable and reports dev-set before/after.
- Every plan and task list MUST include a "Constitution Check" section evaluating the work against
  Principles I-X, naming any principle at risk and how it is satisfied.
- Test-set numbers are produced once, for reporting, and MUST NOT be used to select parameters.

## Governance

This constitution supersedes all other development practices, conventions, and preferences for the
BasisMedic project. Where this document and any other guidance conflict, this document wins.

**Amendment procedure**: An amendment MUST state the reason for the change, identify every
dependent template or command affected, and update those dependents in the same change. Amendments
are recorded by a version bump and an updated **Last Amended** date.

**Versioning policy**: Semantic versioning of governance.
- MAJOR — a principle is removed, or redefined in a way that invalidates prior compliance.
- MINOR — a principle or section is added, or existing guidance is materially expanded.
- PATCH — clarifications, wording, and non-semantic refinements.

**Compliance review**: Every plan and every task list MUST include a "Constitution Check" against
Principles I-X. Reviews reject work that skips a stage gate from the Development Workflow section,
bundles multiple variables into one measured change, trusts model output without code verification,
or reports numbers that the one-command reproduction does not produce. Added complexity MUST be
justified against Principle VI; unjustified complexity is removed, not documented.

**Version**: 1.0.0 | **Ratified**: 2026-11-07 | **Last Amended**: 2026-11-07
