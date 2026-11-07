# Phase 1 Data Model: Triage Agent — Bounded Tool-Calling Loop with Verified Structured Output

**Feature**: `002-triage-agent` | **Date**: 2026-11-08

Maps the entities from [spec.md](./spec.md) onto concrete Pydantic v2 models and on-disk shapes. Every
validation rule cites the requirement it implements. New models live in `app/schemas.py` (shared, same module
Feature 1's `Runbook`/`Chunk`/`Hit` already live in) unless noted; eval-only models live in `eval/`.

---

## Enumerations (extend Feature 1's `app/schemas.py`)

```python
# Category already exists (8 values, from Feature 1). Reused as-is.
# EvalCategory already exists (Category + "out_of_scope"). Reused as-is for TriageResult.category.

Confidence   = Literal["high", "medium", "low"]
FailureTypeE2E = Literal[
    "category_wrong", "tcode_recall_miss", "unverified_claim",
    "repair_exhausted", "loop_exhausted", "schema_invalid_after_fallback",
]
```

`EvalCategory` (already defined by Feature 1: the 8 `Category` values plus `"out_of_scope"`) is reused directly
as `TriageResult.category`'s type — no new category enum is introduced.

---

## 1. Step

One item in a `TriageResult`'s checklist.

| Field | Type | Rules |
|---|---|---|
| `action` | `str` | `min_length=5` — a human-readable instruction (FR-006) |
| `tcode` | `str \| None` | when present, must be a key of `data/tcodes.json` by the time `verify_tcodes` has run; `None` for a step with no associated transaction code |

---

## 2. TriageResult

The validated structured output. Returned by `app.triage_service.triage()`.

| Field | Type | Rules |
|---|---|---|
| `category` | `EvalCategory` | one of the 8 known categories, or `out_of_scope` (FR-006) |
| `summary` | `str` | `max_length=300` — short description of what was found (FR-006) |
| `tcodes` | `list[str]` | `max_length=6`; ordered as they should be opened; every entry verified against the allow-list by the time this is returned (FR-006, FR-010) |
| `unverified_tcodes` | `list[str]` | T-codes the model named that are **not** on the allow-list — recorded, never presented as verified (FR-010, R-06); empty in the common case |
| `steps` | `list[Step]` | `min_length=1, max_length=8` (FR-006) |
| `escalate_to` | `EscalateTo \| None` | reuses Feature 1's `EscalateTo` enum; optional (FR-006) |
| `sources` | `list[str]` | citations, each a `doc_id#section` address; every entry verified to resolve to that request's own Evidence by the time this is returned (FR-006, FR-009); empty **iff** `category == "out_of_scope"` (FR-012) |
| `confidence` | `Confidence` | `"high"`/`"medium"` for a normal result, `"low"` for the R-05 fallback (FR-006) |

**Invariants** (enforced by `verify.py` before a `TriageResult` is ever returned to a caller, FR-009/FR-010/FR-012):

- `category == "out_of_scope"` ⇒ `tcodes == []` **and** `sources == []` (FR-012).
- Every entry in `sources` resolves to a `chunk_id` present in that request's Evidence (FR-009); a citation that
  does not resolve is removed before the result is returned, never left in place.
- Every entry in `tcodes` is a key of `data/tcodes.json`; an entry that is not is moved to `unverified_tcodes`,
  never left in `tcodes` (FR-010).

---

## 3. ToolCallRecord

One tool invocation made during a single triage request's evidence-gathering loop. Not persisted on its own —
lives in request-scoped state and feeds both the repeated-call guard and Evidence assembly.

| Field | Type | Rules |
|---|---|---|
| `tool` | `Literal["search_runbook", "lookup_tcode"]` | which tool (FR-005) |
| `args` | `dict[str, str]` | validated arguments actually dispatched |
| `normalized_key` | `str` | `(tool, normalized args)` — the repeated-call guard's dedup key (R-03) |
| `result` | `str` | the tool's string return value, including a `NO_RELEVANT_RUNBOOK` sentinel when `search_runbook` found nothing (reusing Feature 1's refusal semantics) |
| `hits` | `list[Hit]` | populated only for `search_runbook`: the `Hit`s actually returned — the material that feeds Evidence (R-11) |

---

## 4. Evidence

Not a separate stored model — the flat, order-preserving union of `hits` across every `ToolCallRecord` in one
request where `tool == "search_runbook"` (R-11). The only material `sources` may ever cite (FR-009).

---

## 5. End-to-End RunResult

`eval/results/E4_{config_slug}_{split}.json`, written by `eval/run_e2e.py` — the Feature-2 counterpart of
Feature 1's `RunResult` (same file, mirrored shape, extended with e2e fields).

```text
RunConfig:  experiment="E4", name, split, baseline ("agent" | "E-NoRAG" | "E-ClassicRAG"),
            max_steps, repair_attempts, chat_model, corpus_sha, git_commit
CaseResult: case_id, gold_category, gold_tcodes,
            produced: TriageResult (as returned, post-verification),
            steps_taken: int, repaired: bool, fell_back: bool,
            category_correct: bool, tcode_recall: float,
            unverified_claim: bool  # true if any citation was dropped or any tcode landed in unverified_tcodes
Aggregate:  n_cases,
            category_accuracy, tcode_recall,       # averaged over in-scope cases per 09_eval_plan.md § 2
            unverified_claim_rate, valid_output_rate,
            by_difficulty: { easy|medium|hard|thai|mixed|oos -> same metric block }
```

**Invariants**: `config` records which baseline (if any) produced the row (FR-019); `corpus_sha` and `git_commit`
are copied from the loaded Feature-1 index manifest, never recomputed, same discipline as Feature 1's `RunResult`
(its own FR-035). A run whose `chat_model` disagrees with the configured `CHAT_MODEL` aborts rather than
mislabelling the result, mirroring Feature 1's chunk-strategy mismatch guard.

---

## 6. Comparison (E4)

Not a stored entity — a view `eval/run_all.py` builds over three `RunResult` files (agent, E-NoRAG, E-ClassicRAG)
to emit the E4 section of `results.md` (FR-018, FR-022).

| Field | Meaning |
|---|---|
| `metric` | one of category accuracy, T-code recall, unverified-claim rate, valid-output rate |
| `rows` | the full agent's row plus both named baselines' rows, all on the same split |
| `beats_baseline` | per metric, per baseline: whether the full agent's number is strictly better |
| `verdict` | a generated sentence per metric, stated plainly including when the agent does not beat a baseline (FR-022) |

**Invariant**: all three rows in one E4 comparison share `split` and `corpus_sha` — mirroring Feature 1's E1/E2
`_assert_comparable` guard, reused here rather than reinvented.

---

## 7. FailureRecord (extended)

One line of `eval/results/failures.jsonl` — the same file Feature 1 writes to, extended with new `failure_type`
values (`FailureTypeE2E`, above) alongside Feature 1's retrieval-level ones. A case can appear once per
contributing run (a retrieval-level failure from Feature 1's own headline config, and separately an e2e-level
failure from this feature's agent config, are two distinct records, distinguished by `config_name`).

| Field | Type | Notes |
|---|---|---|
| `case_id` | `str` | |
| `config_name` | `str` | which run produced it (e.g. `"agent"`, `"E-NoRAG"`) |
| `expected_category` | `EvalCategory` | |
| `produced_category` | `EvalCategory` | what the agent actually returned |
| `expected_tcodes` | `list[str]` | `gold_tcodes`, already present on every Feature-1 `EvalCase` |
| `produced_tcodes` | `list[str]` | `tcodes` from the returned `TriageResult` |
| `unverified_tcodes` | `list[str]` | carried from the `TriageResult` for context |
| `failure_type` | `FailureTypeE2E` | which of the six e2e failure modes this is |
| `note` | `str` | the case's own `notes` field, carried through |

**Rule**: `category_wrong` and `tcode_recall_miss` can co-occur on one case (both recorded as context in the
single record, `failure_type` set to whichever is the more specific/primary cause) — mirrors Feature 1's
`partial_recall` treatment of mixed cases rather than inventing a new multi-type scheme.

---

## 8. ChatCacheEntry

`data/chat_cache/<sha256>.json` — generated, git-ignored (R-09). One file per distinct `(model, temperature,
messages, tools)` combination.

```json
{"model": "gemma-4-E4B-it", "temperature": 0, "response": { "...the raw completion..." }}
```

Content-addressed the same way Feature 1's `data/cache/<sha256>.json` embedding cache is — a cache hit is
byte-identical to the original response, which is the mechanism behind FR-020's "identical verification-level
outcomes across two runs" guarantee.

---

## Entity relationships

```text
TriageRequest (one log) ──validated by── the same length bounds as Feature 1's search query
   │
   ▼
Phase 1 loop ──dispatches──> ToolCallRecord* ──search_runbook hits──> Evidence
   │                                              │
   │ (bounded by MAX_STEPS, R-03 guard)           │
   ▼                                              ▼
Phase 2 formatter ──draft JSON──> Step* + draft TriageResult
   │                                              │
   │ (repair ≤ REPAIR_ATTEMPTS, else R-05 fallback)
   ▼                                              │
verify.py ──citations checked against────────────┘
   │        T-codes checked against data/tcodes.json (Feature 1)
   │        out_of_scope forced per R-07 if Evidence is empty
   ▼
TriageResult (returned)
   │
   └── scored against EvalCase.gold_category / gold_tcodes ──> CaseResult ──> RunResult ──> Comparison (E4)
                                                                    │
                                                                    └──failing/fallback/unverified cases──> FailureRecord
```
