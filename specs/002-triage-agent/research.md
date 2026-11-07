# Phase 0 Research: Triage Agent — Bounded Tool-Calling Loop with Verified Structured Output

**Feature**: `002-triage-agent` | **Date**: 2026-11-08

Each entry records a decision, why it was taken, and what was rejected. Unlike Feature 1's research.md (which
resolved genuine open contradictions in an input plan), most entries here formalise decisions the author's own
`docs/prepare/02_design.md` and `04_system_flow.md` already made — recorded here so they are traceable to an FR
and have not been re-litigated without reason.

---

## R-01 — Two phases: evidence-gathering, then formatting, never combined

**Decision**: the agent interacts with the model in two separate calls. Phase 1 exposes `tools=[search_runbook,
lookup_tcode]` and gathers evidence; it ends either when the model stops calling tools (natural stop) or when
`MAX_STEPS` is reached (forced stop). Phase 2 is a single call with no `tools=` parameter, given the gathered
evidence and asked to emit only a JSON object conforming to the `TriageResult` schema.

**Rationale**: `docs/prepare/02_design.md` § 5.3 records, from the course material, that instructing a model to
reply "ONLY JSON" in the same call that also exposes `tools=` suppresses native tool-calling on the course's chat
model (`gemma-4-E4B-it`). Splitting the two concerns is the only way to get both reliable tool-calling and
reliable structured output from this model. This is also recorded in plan.md's Complexity Tracking, since it adds
a second model call per request beyond the conceptual minimum.

**Alternatives considered**: *one call doing both* — the input design explicitly tested this and found it breaks
tool-calling; rejected on the author's own prior evidence, not speculation.

---

## R-02 — Native tool-calling first; a text-based protocol is the documented fallback

**Decision**: the agent's tool-dispatch layer (`app/agent/tools.py` — name, arguments, result, all strings) is
designed so that *how* the model requests a tool call (native function-calling JSON, or a parsed text pattern
like `ACTION: search_runbook("...")`) is an adapter in front of it, not baked into the dispatch logic itself.
Implementation starts with native tool-calling; if early smoke-testing shows the gateway's model does not reliably
emit well-formed tool calls, the text-protocol adapter (already sketched by the course's reference app) is
substituted with no change to `tools.py`, `verify.py`, or anything downstream.

**Rationale**: `docs/prepare/00_START_HERE.md` names this the project's #1 risk ("ทดสอบ proxy วันแรก โดยเฉพาะ
native tool calling ของ gemma") and `02_design.md` § 5.4 already names the fallback. The spec's own Assumptions
section treats the mechanism as a planning-phase choice, not something fixed by the spec. Designing the dispatch
boundary so the adapter is swappable is what keeps the fallback a one-file change rather than a rewrite.

**Alternatives considered**: *commit to native tool-calling only, add the fallback later if needed* — rejected
because retrofitting the adapter boundary after `verify.py`/`formatter.py` are written against a specific call
shape is more invasive than designing the boundary in from the start, for near-zero extra cost now.

---

## R-03 — Repeated-call guard keys on (tool name, normalized arguments), scoped to one request

**Decision**: before dispatching a tool call, the loop checks whether `(tool_name, normalized_args)` has already
been dispatched in this same triage request. If so, the call is not re-executed; the loop is told it already has
that result and must proceed differently. "Normalized" means the same case-folding and whitespace-collapsing
Feature 1's `eval/schema.py` already uses for its cross-split duplicate-log check — reused rather than
reinvented. The guard is scoped to one request only; it does not persist across separate triage calls.

**Rationale**: FR-004 requires the guard; the spec leaves the exact dedup key open. Keying on normalized
arguments (not raw string equality) is needed so `search_runbook("TSV_TNEW_PAGE_ALLOC_FAILED")` and
`search_runbook("  TSV_TNEW_PAGE_ALLOC_FAILED ")` are correctly recognised as the same call — a model is as
likely to vary whitespace as phrasing.

**Alternatives considered**: *exact string match only* — simpler, but would let trivial whitespace variation
defeat the guard, which is precisely the failure mode FR-004 exists to prevent. *Semantic similarity matching* —
rejected as unjustified complexity for a guard whose job is catching near-exact repeats, not paraphrases.

---

## R-04 — `MAX_STEPS` is env-configured; the repair cap is a code constant

**Decision**: `MAX_STEPS` (bounding the evidence-gathering loop) stays an environment variable — `.env.example`
already reserves it at `5`, unused until this feature. The repair-attempt cap (bounding Phase 2's retry loop) is a
code constant, `REPAIR_ATTEMPTS = 2`, not a new environment variable.

**Rationale**: `MAX_STEPS` is genuinely a deployment-relevant knob (a slower or flakier gateway might justify a
different bound) and was already designed as configuration before this feature existed. The repair cap is a
correctness bound on a formatter retry loop — tuning it is not a deployment decision in the way `MAX_STEPS` is,
and Feature 1 already established the precedent of keeping similar bounds (the `MIN_SCORE` sweep's floor range,
E1/E2's experiment matrix) as code rather than environment configuration when they are structural to the
algorithm rather than site-specific.

**Alternatives considered**: *both as env vars* — Constitution V says configuration must come from environment
variables, but its own compliance check and Feature 1's own practice read that as applying to genuine deployment
configuration (model names, secrets, floors that get tuned per-corpus), not every numeric constant in the
codebase; a `REPAIR_ATTEMPTS` env var would be dead configuration nobody would ever have reason to change
independently of the code that interprets it. *Both as code constants* — rejected because `MAX_STEPS` is already
committed, documented configuration surface from Feature 1; changing that now would be unjustified churn.

---

## R-05 — The fallback is deterministic, uses no model call, and still satisfies the full schema

**Decision**: when the repair loop (R-01's Phase 2) exhausts its attempts, `app/agent/fallback.py` builds a
`TriageResult` directly from the single best-scoring item in Evidence: `category` from that runbook's own
category, `steps` derived by splitting its `## Check` section's numbered list (the same numbered-T-code-step
format Feature 1's corpus already enforces — `contracts/file-formats.md` § 1 in Feature 1's spec), `tcodes` from
that runbook's own front-matter `tcodes` list, `escalate_to` from that runbook's own front-matter, `sources` set
to that one runbook's citation, and `confidence` fixed to `"low"`. No further model call is made.

**Rationale**: FR-008 requires the fallback to be deterministic and to itself satisfy FR-006's schema. Building it
from a runbook's own already-validated front-matter (every field Feature 1's `Runbook` Pydantic model already
guarantees: 1–8 ordered tcodes, a known `escalate_to` enum, a non-empty `Check` section) means the fallback cannot
itself fail validation — the one thing the system must never do when it is already in the degraded path.

**Alternatives considered**: *a simpler one-shot model call with no tools, hoping for cleaner JSON* — rejected:
still subject to the same validation failure it is meant to be the safety net for. *Return an error instead of a
fallback result* — rejected, since FR-008 and SC-001 explicitly require a structurally valid result even in the
worst case; an error response here would mean the system crashed from the caller's point of view.

---

## R-06 — Citation verification and T-code verification are two independent checks, not one

**Decision**: `app/agent/verify.py` exposes two separate functions. `verify_citations(result, evidence)` drops
any citation not present in that request's actual Evidence. `verify_tcodes(result, allow_list)` partitions the
response's T-codes into verified (stay in `tcodes`) and unverified (moved to a separate `unverified_tcodes` field,
never silently dropped).

**Rationale**: the two checks have genuinely different correct behaviour on failure — a fabricated citation is
simply wrong and is removed, but a T-code outside the allow-list might be a real SAP transaction the author's
corpus simply never catalogued; recording it as `unverified_tcodes` rather than deleting it is what makes the
hallucination-rate metric (FR-016) honestly countable instead of invisible. Keeping them as two functions (not one
combined "sanitize" step found during Phase 1 design — see plan.md's Post-Design Re-Check) is also what makes each
independently unit-testable per Constitution VIII.

**Alternatives considered**: *one combined verification function* — simpler on the surface, but conflates two
different failure semantics (drop vs. flag) and two different metrics (citation resolvability is implicit in
SC-002; `unverified_tcodes` is what FR-016's hallucination rate is computed from) into one code path, making both
harder to test and harder to reason about independently.

---

## R-07 — `out_of_scope` is forced after the loop ends, by checking every retrieval call's outcome

**Decision**: when Phase 1 (evidence-gathering) ends, the loop's `ToolCallRecord`s are inspected: if every
`search_runbook` call returned no relevant result (Feature 1's `NO_RELEVANT_RUNBOOK` / empty-hit-list outcome),
the eventual `TriageResult`'s `category` is overwritten to `out_of_scope` — and `tcodes`/`sources` cleared to
match FR-012 — regardless of what the Phase 2 formatter produces. This check runs *before* Phase 2 is even
called when Evidence is empty, skipping the formatter call entirely in that case (no evidence exists for it to
format).

**Rationale**: FR-011 requires the forcing rule to override the model's own assertion, which only a code-side
check after the loop (not a prompt instruction) can guarantee — Constitution IV's entire premise is that prompt
instructions are not trusted. Checking "every search call" rather than "the last search call" matters for
multi-search cases (User Story 1 scenario 3): a case that searches twice, finding nothing the first time and
something real the second time, must not be forced out of scope just because one of its calls came back empty.

**Alternatives considered**: *ask the model to decide `out_of_scope` itself when it sees `NO_RELEVANT_RUNBOOK`* —
exactly what FR-011 forbids: Constitution III requires the system to never ask the model to guess when nothing
clears the floor. *Force out_of_scope on the first empty search rather than checking all of them* — rejected,
would incorrectly refuse the legitimate multi-search case above.

---

## R-08 — Baselines are defined as alternate paths through the same validate/verify pipeline

**Decision**:

| Baseline | What it skips | What it still does |
|---|---|---|
| **E-NoRAG** | Phase 1 entirely — no tools exposed, no retrieval call made | Phase 2 formatter call (asked to answer directly from the normalized log), then the *same* `verify.py` checks |
| **E-ClassicRAG** | The agent loop's *iteration* — exactly one `search_runbook` call is made with the normalized log as the query, no further searches regardless of result | Phase 2 formatter call over that single search's evidence, then the *same* `verify.py` checks |
| **Full agent** | Nothing | Everything |

Both baselines are run through the identical `verify_citations`/`verify_tcodes`/R-07 out-of-scope-forcing logic
the full agent uses — a baseline's hallucination rate is not measured leniently.

**Rationale**: the spec (FR-018) requires the comparison to isolate what the agent loop and retrieval each
contribute. Running every configuration through the same verification pipeline is what makes the four metrics
genuinely comparable across rows — exactly Feature 1's R-07 principle (`search()` collapses results identically
for every caller) applied to this feature's service layer. If E-NoRAG's verification were skipped or lenient, its
hallucination rate would be artificially low for the wrong reason (nothing was checked), not because it is
actually more careful.

**Alternatives considered**: *E-NoRAG with no verification at all, scored purely on the model's raw claims* —
rejected: would not be measuring hallucination at all, since an unverified claim and a verified one would look
identical in the output.

---

## R-09 — Chat completions are cached on disk, content-addressed, mirroring Feature 1's embedding cache

**Decision**: `app/llm.py`'s new `chat()` function is wrapped with a disk cache at `data/chat_cache/`, key
`sha256(f"{model}|{temperature}|{json.dumps(messages, sort_keys=True)}|{json.dumps(tools or [], sort_keys=True)}")`,
value the raw completion. A cache hit never calls the gateway. Git-ignored, same as Feature 1's `data/cache/`.

**Rationale**: FR-020 requires two consecutive end-to-end runs to produce identical verification-level outcomes.
A full E4 run makes many chat calls across 3 configurations x 30 test cases; content-addressed caching makes
repeats both free and outcome-stable, removing dependence on upstream sampling variance this project does not
control — the same justification Feature 1's R-09 gave for the embedding cache, now applied to the chat side.
Including `tools` and `temperature` in the key (not just `messages`) matters specifically because Phase 1 and
Phase 2 calls share a model and often overlapping message prefixes but differ in exactly those two fields — a
key that omitted them would silently conflate two different calls.

**Alternatives considered**: *no chat cache, rely on `temperature=0`* — temperature 0 reduces but does not
guarantee determinism (upstream model/infra changes can still shift output between runs, as Feature 1's own
research.md R-09 notes for embeddings); a real cache is the difference between assuming reproducibility and
guaranteeing it. *A single cache directory shared with the embedding cache* — rejected as a minor readability
loss for no real gain; two independently inspectable, independently clearable caches is simpler to reason about
than one with two differently-keyed entry types.

---

## R-10 — The agent reuses Feature 1's `normalize.py` as-is; no new log-cleaning logic

**Decision**: the raw pasted log is passed through Feature 1's existing `strip_noise()`, `cap_length()`, and
`extract_key_tokens()` before it ever reaches Phase 1's system/user prompt — the same pipeline `search()` already
applies to a query. No second implementation of timestamp-stripping, address-stripping, or key-token extraction is
written for this feature.

**Rationale**: `docs/prepare/04_system_flow.md` § B2 describes exactly the normalization Feature 1 already built
and tested (`tests/test_normalize.py`). Writing a second copy for the agent would duplicate logic that already
has committed test coverage, and risks the two copies drifting apart over time — the dependency goes one
direction only (agent depends on Feature 1's normalize, never the reverse), consistent with Constitution VI's
inward-only dependency rule.

**Alternatives considered**: *write agent-specific normalization* — no stated requirement differs between what
`search()` needs and what the agent's Phase 1 prompt needs; reusing is strictly simpler and was the obvious
default once confirmed the existing function signatures fit.

---

## R-11 — Evidence is exactly the retrieved `Hit`s, not a re-derived or re-ranked view of them

**Decision**: `Evidence` (the key entity citations are checked against) is defined as the flat, order-preserving
list of every `Hit` returned by every successful `search_runbook` call made during one request — no deduplication
beyond what `search()` itself already guarantees (distinct `doc_id` per call), no re-ranking across calls, no
truncation.

**Rationale**: FR-009 requires citation verification against "evidence actually returned by `search_runbook`" —
the simplest, least error-prone definition is the literal union of what was returned, with no additional
transformation that could itself introduce a bug between "what was shown to the model" and "what verification
checks against." A re-ranked or deduplicated-across-calls view would require the verification code to reconstruct
exactly what the model saw, which is extra complexity in service of no requirement.

**Alternatives considered**: *deduplicate Evidence across multiple `search_runbook` calls within one request* —
rejected as unneeded complexity: a `chunk_id` cited from either of two calls that returned it is still a valid
citation either way, so deduplication would change nothing about *correctness*, only save a small amount of
memory, at the cost of a reconciliation step that is itself a place for bugs.

---

## R-12 — Task ordering: metric functions and the agent's unit-tested guarantees come before real wiring

**Decision**: implementation proceeds in this order, mirroring Feature 1's R-12 but without a Constitution-I
eval-set gate (none is needed — Feature 1's eval set already exists and needs no new cases):

1. `app/llm.py:chat()` + chat cache — still no agent logic, parallel in spirit to Feature 1's `app/llm.py:embed()`
   step.
2. `app/schemas.py`: `TriageResult`, `Step` + unit tests — schema and semantic-validation rules fixed before
   anything produces them.
3. `app/agent/tools.py`, `verify.py`, `fallback.py` + unit tests — the parts whose correctness is fully knowable
   without ever calling a real model (Constitution VIII).
4. `app/agent/loop.py`, `formatter.py` + unit tests with `chat()` mocked — the two-phase interaction (R-01),
   `MAX_STEPS` bound, repeated-call guard (R-03), repair loop.
5. `app/triage_service.py` wiring it all together + `app/cli.py`'s `triage` subcommand.
6. `eval/run_e2e.py`'s four metric functions + hand-computed-fixture tests — before the baselines are run for
   real, same discipline as Feature 1's `eval/metrics.py`.
7. `eval/run_e2e.py`'s three configurations (agent, E-NoRAG, E-ClassicRAG per R-08) wired to the real `chat()` →
   first real end-to-end numbers.
8. `eval/run_all.py` extended with the E4 table; `failures.jsonl` extended with agent-specific failure types.

**Rationale**: this is the same "measurement machinery before the thing it measures is trusted" discipline
Feature 1's R-12 established, adapted to the fact that this feature's "evaluation-first" gate was already cleared
by Feature 1 committing the eval set before any Feature-2 code existed at all.

**Alternatives considered**: *build the agent loop first, write eval last* — the natural instinct the
constitution's Principle VII build order exists specifically to prevent; it risks shaping the verification logic
around whatever the agent happens to produce rather than around the spec's requirements.

---

## Resolved unknowns

No `NEEDS CLARIFICATION` markers remain in plan.md's Technical Context. For the record, the questions genuinely
open before this research pass:

| Queued question | Landed in |
|---|---|
| Will native tool-calling work reliably on the course gateway's model? | R-02 (native first, swappable adapter, not a blocking unknown) |
| What exactly counts as a "repeated" tool call? | R-03 (normalized `(tool, args)` pair, per-request) |
| Should the repair cap be configurable? | R-04 (no — code constant, `MAX_STEPS` stays the one env-configured bound) |
| How is the fallback guaranteed to itself pass validation? | R-05 (built from already-validated Runbook fields) |
| Is a fabricated T-code dropped or flagged? | R-06 (flagged, in `unverified_tcodes` — never silently dropped) |
| When exactly is `out_of_scope` forced? | R-07 (after the loop, checking every search call's outcome) |
| Do baselines get an easier ride on verification? | R-08 (no — identical pipeline for every configuration) |
| Is e2e reproducibility assumed or guaranteed? | R-09 (guaranteed, via a chat cache) |
