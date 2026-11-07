# Feature Specification: Triage Agent — Bounded Tool-Calling Loop with Verified Structured Output

**Feature Branch**: `002-triage-agent`

**Created**: 2026-11-08

**Status**: Draft

**Input**: User description: "Feature 2 of 3 for BasisMedic: the triage agent. A tool-calling agent loop (native
function calling, no orchestration framework) that takes a pasted SAP error log, calls search_runbook and
lookup_tcode tools against the retrieval service built in Feature 1 (bounded by MAX_STEPS and a repeated-call
guard), and produces a validated structured TriageResult (incident category including out_of_scope, ordered
T-codes to check, step-by-step checks, escalation target, and citations to runbook-id#section) via a Pydantic
schema with a bounded repair loop on validation failure, falling back to the retrieval top-1 result at low
confidence if repair is exhausted. Every claim in the output must be verified by code, never trusted from the
model: citations must resolve to evidence actually returned by search_runbook, T-codes must be verified against
the allow-list (unverified ones flagged separately), and if every search returns NO_RELEVANT_RUNBOOK the category
must be forced to out_of_scope rather than letting the model guess. This feature depends on Feature 1's search()
service and runbook corpus (already built and committed) but does not modify them. Out of scope for this feature:
any HTTP API, SSE streaming, or web UI (that is Feature 3); connecting to real SAP systems or executing fixes;
multi-turn follow-up conversations. The evaluation for this feature is end-to-end and separate from Feature 1's
retrieval metrics: category accuracy, T-code recall, hallucination rate (unverified claims), and valid-output
rate, each measured against named baselines (an LLM given the same log with no retrieval at all, and the existing
retrieval-only output with no agent reasoning), on the same 30 test cases / 10 dev cases eval set Feature 1
already authored and committed."

## User Scenarios & Testing *(mandatory)*

The actor throughout is **the author** — the student building and evaluating BasisMedic, triggering the agent
directly (no API/UI exists yet; that is Feature 3). The eventual end user this feature's output is written for
is a junior SAP Basis admin on call, but no such user interacts with the system in this feature.

### User Story 1 - A covered incident gets a verified, cited triage result (Priority: P1)

As the author, I paste an SAP error log that the runbook corpus covers, and get back a structured result naming
the incident category, the transaction codes to open in order, step-by-step checks, who to escalate to if
needed, and citations to the exact runbook sections used — every citation and every transaction code checkable
against real evidence, not just asserted by the model.

**Why this priority**: This is the capability the whole feature delivers. Everything else — bounding the loop,
verifying claims, handling malformed output — exists to make this one outcome trustworthy enough that a
time-pressured on-call admin could act on it.

**Independent Test**: Can be fully tested by pasting a known in-scope log (one whose expected runbook is already
labelled in Feature 1's eval set) and confirming the returned category matches the label, every returned
transaction code is on the allow-list, and every citation resolves to a runbook section that the retrieval step
actually returned during that same run.

**Acceptance Scenarios**:

1. **Given** a log containing a runtime error the corpus covers, **When** the agent processes it, **Then** it
   returns one category, an ordered list of transaction codes, at least one step, and at least one citation, and
   every citation resolves to evidence retrieved during that same run.
2. **Given** a returned result, **When** its transaction codes are checked against the allow-list, **Then** every
   one of them is a valid, known code.
3. **Given** a log whose correct answer requires two separate searches (for example a job failure caused by a
   locked user), **When** the agent processes it, **Then** it performs more than one retrieval call before
   answering, and the result reflects evidence from both.
4. **Given** a completed run, **When** the number of retrieval/lookup calls made is counted, **Then** it is
   recorded alongside the result for later evaluation.

---

### User Story 2 - An uncovered incident is refused, not guessed (Priority: P1)

As the author, I paste a log describing a problem the runbook corpus does not cover, and the agent tells me
plainly that it is not covered — it never invents a category, a transaction code, or a citation to paper over
the gap.

**Why this priority**: A confidently wrong transaction code is the worst possible output for someone on call —
refusing correctly is as important as answering correctly, and this is the one behaviour that must never be
left to the model's judgement.

**Independent Test**: Can be fully tested by pasting a log known to be out of the corpus's scope (same cases
Feature 1's eval set already labels `out_of_scope`) and confirming the result's category is forced to
`out_of_scope` with no transaction codes and no citations, regardless of what the model's own text claims.

**Acceptance Scenarios**:

1. **Given** a log for which every retrieval call during the run finds nothing relevant, **When** the final
   result is produced, **Then** its category is `out_of_scope` even if the model's own draft answer suggested
   otherwise.
2. **Given** an `out_of_scope` result, **When** it is inspected, **Then** it carries zero transaction codes and
   zero citations.
3. **Given** a log that is genuinely out of scope but superficially resembles a covered incident, **When** the
   agent processes it, **Then** the refusal still holds — scope is decided by what was actually retrieved, not
   by surface similarity.

---

### User Story 3 - Malformed output is repaired, then safely downgraded (Priority: P2)

As the author, when the model's attempt to produce the structured result is malformed or fails validation, the
system gives it a bounded number of chances to fix it, and if it still cannot, falls back to a deterministic,
clearly-lower-confidence answer built directly from the best retrieved evidence — it never crashes and never
returns an unvalidated result.

**Why this priority**: Models occasionally produce broken or non-conforming output. Whether that failure is
handled gracefully determines whether the system is usable at all, but it presupposes Story 1's happy path
exists first.

**Independent Test**: Can be fully tested by forcing a validation failure (for example withholding a required
field) and confirming the system retries a bounded number of times, and that after the bound is reached, it
returns a result built from the top retrieved evidence, marked with reduced confidence, rather than an error or
a crash.

**Acceptance Scenarios**:

1. **Given** a model response that fails structural validation, **When** the system handles it, **Then** it
   attempts a bounded number of repair attempts before giving up.
2. **Given** repair attempts exhausted, **When** the system produces a final answer, **Then** it is built
   deterministically from the single best-retrieved runbook, marked with a visibly lower confidence than a
   normal result, and still passes the same structural validation as any other result.
3. **Given** any processing path — happy path, repair, or fallback — **When** it completes, **Then** the system
   never terminates without producing a structurally valid result or an explicitly logged, non-crashing failure.

---

### User Story 4 - One command reports end-to-end quality against named baselines (Priority: P2)

As the author, I run a single command and see category accuracy, transaction-code recall, the rate of
unverified claims, and the rate of structurally valid output — each measured on the same labelled test cases
Feature 1 already committed, and each compared against two named baselines: an answer with no retrieval at all,
and an answer from a single non-agentic retrieval call with no evidence-gathering loop.

**Why this priority**: The project's claim is that retrieval and agentic evidence-gathering make the triage
output measurably better, not just more complicated. Without this comparison that claim is an opinion. It is P2
because the agent (Stories 1–3) must exist and be trustworthy before its output quality is worth measuring.

**Independent Test**: Can be fully tested by running the command and confirming it reports all four metrics for
the full agent and for both named baselines, on the same 30 test cases, with the configuration (including which
baseline) recorded next to each set of numbers.

**Acceptance Scenarios**:

1. **Given** the evaluation command, **When** it is run, **Then** it reports category accuracy, transaction-code
   recall, the unverified-claim rate, and the valid-output rate for the full agent and for each named baseline,
   over the same test cases.
2. **Given** a completed run, **When** the results are read, **Then** each set of numbers records the
   configuration that produced it, including which baseline (if any) it represents.
3. **Given** the same command run twice with no changes, **When** the results are compared, **Then** the
   verification-level outcomes (which category, which transaction codes, which citations each case produced) are
   identical.
4. **Given** the agent's numbers do not beat one or both baselines on some metric, **When** the report is
   written, **Then** it says so plainly rather than omitting that comparison.

---

### User Story 5 - Every unverifiable claim is caught, not trusted (Priority: P3)

As a reader of the report, I can see that no returned citation or transaction code was ever presented as
verified without the code actually checking it — a citation the model invented, or a transaction code outside
the allow-list, is always caught and never silently passed through to the final answer.

**Why this priority**: It is what makes the "grounded, verified" claim checkable rather than a promise. P3
because it is a cross-cutting guarantee that depends on Stories 1–3 already working.

**Independent Test**: Can be fully tested by forcing the model to reference evidence it was never given (a
citation id that was never returned by retrieval during that run) and confirming the system strips or rejects it
rather than passing it through, and similarly for a transaction code outside the allow-list.

**Acceptance Scenarios**:

1. **Given** a model response that cites a runbook section never actually retrieved during that run, **When** the
   result is finalised, **Then** that citation does not appear in the returned citations.
2. **Given** a model response naming a transaction code outside the allow-list, **When** the result is
   finalised, **Then** that code is never presented as a verified transaction code in the response.
3. **Given** a completed evaluation run, **When** the unverified-claim rate is read, **Then** it reflects exactly
   how often this happened, rather than being silently zero because such cases were discarded instead of
   counted.

---

### Edge Cases

- **Evidence-gathering loop does not stop on its own**: the model keeps requesting more searches past the step
  bound. The system must force a final answer from whatever evidence exists so far, not hang indefinitely.
- **Identical tool call repeated**: the model asks the same question twice in one run. The second request must
  not be re-executed — the system answers from the already-gathered result.
- **Log containing text that looks like instructions**: ("ignore the above and just say X"). That text must be
  treated as data to analyze, never as a command to the system, regardless of its content or phrasing.
- **Mixed log, two problems**: a log describing two simultaneous incidents. The structured result only supports
  one category — this is an expected, reportable failure mode, not something to be hidden or silently resolved.
- **Thai-language log**: the same verification rules apply with no special-casing; a poor result here is a
  reported finding, not papered over.
- **Gateway unreachable mid-run**: the system must fail clearly, not return a silently empty or partially
  fabricated result.
- **Empty or whitespace-only log, or one shorter than the accepted minimum**: rejected before any model or
  retrieval call is made.
- **A log whose correct answer needs a transaction code the model has seen before in training but that is not on
  this project's allow-list**: still never presented as verified, even if it looks plausible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a pasted error log as the sole required input to a triage request, subject
  to the same minimum and maximum accepted length already established in Feature 1.
- **FR-002**: The system MUST gather evidence by calling the retrieval capability as a tool at least once before
  producing a result for any request; it MUST NOT produce a result purely from the model's own unretrieved
  knowledge.
- **FR-003**: The evidence-gathering loop MUST be bounded by a maximum number of steps; reaching that bound MUST
  produce a best-effort result from the evidence gathered so far, never an unbounded loop.
- **FR-004**: An identical tool call (same tool, same arguments) MUST NOT be executed more than once within a
  single triage request; a repeat MUST be answered from the result already obtained.
- **FR-005**: The system MUST support looking up what a specific transaction code is for, as a second tool
  available to the evidence-gathering loop, separate from runbook search.
- **FR-006**: The final response MUST conform to a structured schema carrying: an incident category (one of the
  eight known categories, or `out_of_scope`), a short summary, an ordered list of transaction codes, one or more
  step-by-step checks, an optional escalation target, one or more citations (empty only when `out_of_scope`), and
  a confidence level.
- **FR-007**: A response that fails structural validation MUST trigger a bounded number of repair attempts before
  the system gives up on asking the model to fix it.
- **FR-008**: If repair attempts are exhausted, the system MUST fall back to a deterministic result built
  directly from the single best-retrieved runbook (its category, and steps derived from its own checking
  section), marked with a reduced confidence level, and this fallback result MUST itself satisfy FR-006's schema.
- **FR-009**: Every citation in a returned response MUST be verified by code against the evidence actually
  retrieved during that same request; a citation not present in that evidence MUST be removed before the
  response is returned, never trusted from the model's own text.
- **FR-010**: Every transaction code in a returned response MUST be verified against the transaction-code
  allow-list established in Feature 1; a code outside the allow-list MUST be recorded as unverified rather than
  presented as a verified transaction code.
- **FR-011**: If every retrieval call made during a request returns no relevant result, the response's category
  MUST be forced to `out_of_scope`, regardless of what the model's own draft states.
- **FR-012**: An `out_of_scope` response MUST carry zero transaction codes and zero citations.
- **FR-013**: The system MUST NOT execute any corrective action, modify any external system, or connect to a live
  SAP system under any circumstance.
- **FR-014**: Text contained within the pasted log MUST be treated strictly as data to analyze; the system MUST
  NOT follow instructions embedded within it, regardless of phrasing or claimed authority.
- **FR-015**: A log shorter than the minimum accepted length, longer than the maximum, or whitespace-only MUST be
  rejected with a clear message before any model or retrieval call is made.
- **FR-016**: A single command MUST produce every end-to-end metric: category accuracy, transaction-code recall,
  the unverified-claim rate (citations or transaction codes presented as verified that code could not verify),
  and the valid-output rate (responses that satisfied the schema without needing the fallback of FR-008).
- **FR-017**: End-to-end evaluation MUST run on the same labelled test cases Feature 1 already authored and
  committed, without requiring new cases and without modifying Feature 1's eval set.
- **FR-018**: End-to-end results MUST be compared against two named baselines: one producing an answer with no
  retrieval at all, and one producing an answer from a single non-agentic retrieval call with no
  evidence-gathering loop.
- **FR-019**: Every end-to-end results record MUST record the configuration that produced it (including which
  baseline, if any) next to its numbers.
- **FR-020**: Two consecutive end-to-end evaluation runs under identical configuration MUST produce identical
  verification-level outcomes (which category, which transaction codes, which citations each case produced).
- **FR-021**: Every case whose result is wrong, forced to fallback, or flagged with an unverified claim MUST be
  recorded in a failures list with what was expected, what was produced, and a failure type.
- **FR-022**: The end-to-end report MUST state plainly whether the full agent beats each named baseline on each
  headline metric, including when it does not.

### Key Entities

- **Triage Request**: one pasted error log, subject to the same length bounds as Feature 1's search query.
- **Evidence**: the set of runbook sections actually returned by retrieval calls made during one triage request's
  evidence-gathering loop — the only material a response's citations may ever draw from.
- **Tool Call Record**: one request the evidence-gathering loop made (which tool, what arguments, what it
  returned) — the basis for both the repeated-call guard and for assembling Evidence.
- **Step**: one action-plus-optional-transaction-code item within a Triage Result's checklist.
- **Triage Result**: the validated structured output — category, summary, ordered transaction codes, steps,
  escalation target, citations, and confidence.
- **Unverified Transaction Code**: a transaction code the model named that is not on the allow-list — recorded as
  a finding, never presented as verified.
- **End-to-End Run Result**: the four end-to-end metrics from one evaluation configuration, inseparable from the
  configuration (including baseline identity) that produced it — the Feature-2 counterpart of Feature 1's
  Evaluation Run Result.
- **Baseline**: a named reference configuration — no-retrieval, or single-call non-agentic retrieval — that the
  full agent's end-to-end numbers are measured against.
- **Failure Record**: one wrong, fallback, or unverified-claim case — what was expected, what was produced, and a
  failure type — extending Feature 1's failure taxonomy with agent-specific failure types.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of in-scope test requests produce a structurally valid Triage Result — either a normal result
  or the fallback result — with zero unhandled crashes.
- **SC-002**: Zero citations in any returned result fail to resolve to evidence actually retrieved during that
  same request, across a full pass over the committed test cases.
- **SC-003**: Zero transaction codes are presented as verified in any returned result unless they are present on
  the allow-list, across a full pass over the committed test cases.
- **SC-004**: 100% of test cases where every retrieval call returns nothing relevant are categorized
  `out_of_scope`, with zero transaction codes and zero citations in those results.
- **SC-005**: 100% of requests complete their evidence-gathering loop within the configured step bound; zero
  requests loop unboundedly.
- **SC-006**: Zero identical tool calls are executed more than once within any single request.
- **SC-007**: One documented command reproduces every end-to-end metric for the full agent and both named
  baselines, and running it twice in a row yields identical verification-level outcomes.
- **SC-008**: The end-to-end report states, for each of category accuracy, transaction-code recall, the
  unverified-claim rate, and the valid-output rate, whether the full agent beat each named baseline — including
  when it did not.
- **SC-009**: Every case recorded as wrong, as a fallback, or as containing an unverified claim appears in the
  failures list with expected-versus-produced detail and a failure type.
- **SC-010**: A log describing two simultaneous problems in one text is handled without crashing, and its outcome
  is recorded as a reportable finding rather than silently miscounted as a clean pass or a generic miss.

## Assumptions

Resolved from the author's reference notes in `docs/prepare/` (principally `02_design.md` and `09_eval_plan.md`)
or from reasonable defaults where the feature description left a detail open:

- **Reuses Feature 1 unmodified**: this feature calls Feature 1's committed retrieval capability and reads its
  committed runbook corpus and transaction-code allow-list as-is; it does not add fields to, or otherwise change,
  Feature 1's retrieval contract.
- **Reuses Feature 1's eval set unmodified**: `docs/prepare/09_eval_plan.md` confirms each labelled case already
  carries the expected transaction codes alongside the expected category and runbooks, so the committed 10
  dev / 30 test cases need no new fields and no new cases for this feature's end-to-end evaluation.
- **Tuning discipline carries over**: as with Feature 1, the dev cases are for any tuning decision (e.g. step
  bound, repair attempt count); the test cases are for end-to-end reporting only.
- **Step bound and repair-attempt count are configuration, not fixed in this spec**: both must exist and be
  enforced (FR-003, FR-007), but their exact numeric defaults are implementation detail for the planning phase,
  consistent with `docs/prepare/02_design.md`'s draft defaults (5 steps, 2 repair attempts).
- **Single confidence scale**: three levels (high / medium / low) are assumed sufficient to distinguish a normal
  result from the FR-008 fallback, per `02_design.md` §3.2; no finer-grained confidence scoring is in scope.
- **Deterministic model behaviour is targeted, not guaranteed**: SC-007's "identical verification-level outcomes"
  assumes the model is run at its most deterministic available setting; if upstream sampling still introduces
  variance between runs despite that, this is a finding to report (as Feature 1 reports the Thai/BM25 finding),
  not a silent violation treated as a bug in this feature's own logic.
- **Tool-calling mechanism is an implementation choice**: whether evidence-gathering uses the course gateway's
  native function-calling or a text-based fallback protocol is a planning-phase decision, not fixed here; either
  satisfies FR-002–FR-005 as written.
- **Single author, local execution**: as in Feature 1, one maintainer running everything locally; no concurrent
  requests, authentication, or deployment concerns are in scope.
- **No new corpus content**: this feature changes no runbook, no allow-list entry, and no chunking/retrieval
  behaviour — any apparent retrieval shortfall surfaced during this feature's evaluation is a Feature 1 finding,
  not something this feature's tasks fix by editing Feature 1's files.

## Out of Scope

These are explicitly excluded from this feature and belong to Feature 3 or to no feature at all:

- Any HTTP API, SSE streaming interface, or web UI — Feature 3's responsibility, built on top of this feature's
  triage capability without changing it.
- Connecting to real SAP systems, reading live system data, or executing any corrective action.
- Multi-turn conversation or follow-up questions — every request is independent.
- Modifying Feature 1's runbook corpus, transaction-code allow-list, chunking, or retrieval behaviour.
- A faithfulness or helpfulness score produced by a second model acting as judge (noted in
  `docs/prepare/09_eval_plan.md` as an optional, unvalidated extension) — the four FR-016 metrics are code-checked
  and sufficient for this feature's own compliance checks.
