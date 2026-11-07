# Contract: `triage()` service (`app/triage_service.py`)

**Feature**: `002-triage-agent` | **Layer**: service

The single triage entry point. The CLI and the eval harness call this exact function with the same arguments, so
the measured system and the demonstrated system cannot diverge — the same discipline Feature 1's `search()`
established (Constitution VI).

```python
def triage(
    log: str,
    *,
    mode: Literal["agent", "E-NoRAG", "E-ClassicRAG"] = "agent",  # baseline selector, R-08
    store: Store | None = None,       # injected for tests; loaded from data/index/ otherwise
) -> TriageResult:
    ...
```

Always returns a `TriageResult` that satisfies its own schema (data-model.md § 2) — never a partial, never an
exception for a well-formed request. Only raises for the edge-validation and infrastructure failures listed under
Errors below.

---

## Pipeline

```
log
  ├─ 1. validate            same length bounds as Feature 1's search() (10-4000 chars), InvalidQueryError
  ├─ 2. normalize           app.normalize.strip_noise/cap_length/extract_key_tokens (R-10) — no new logic
  ├─ 3. Phase 1              mode="agent"/"E-ClassicRAG": gather Evidence via tool call(s) (R-01, R-08)
  │                          mode="E-NoRAG": skipped entirely, Evidence = []
  ├─ 4. out_of_scope check  if Evidence is empty, skip to step 7 with category forced out_of_scope (R-07)
  ├─ 5. Phase 2 formatter   draft TriageResult from Evidence (+ the log's own text for E-NoRAG)
  ├─ 6. repair loop         ≤ REPAIR_ATTEMPTS attempts if structural validation fails; else R-05 fallback
  └─ 7. verify               verify_citations + verify_tcodes + (if step 4 triggered) force out_of_scope
```

Step 4 can short-circuit steps 5–6 entirely: if nothing was ever retrieved, there is no Evidence for the
formatter to work from, and no model call is spent producing a draft that would be discarded anyway.

---

## Modes (R-08)

| Mode | Phase 1 behaviour | Used by |
|---|---|---|
| `agent` | Full bounded loop: up to `MAX_STEPS` tool calls, repeated-call guard, natural or forced stop | the shipped CLI `triage` subcommand; the E4 "agent" row |
| `E-ClassicRAG` | Exactly one `search_runbook` call with the normalized log as the query; no further searching regardless of result | the E4 `E-ClassicRAG` baseline row only |
| `E-NoRAG` | No tool calls at all; Phase 2 is given the normalized log directly instead of Evidence | the E4 `E-NoRAG` baseline row only |

All three modes pass through the identical Phase 2 formatter, repair loop, and `verify.py` checks (R-08) — a
baseline's hallucination rate is measured exactly as strictly as the full agent's.

---

## Guarantees

1. **Never an invalid result.** Every call either returns a `TriageResult` passing its own schema (normal or R-05
   fallback) or raises one of the Errors below — never an exception from inside the formatting/repair/verify
   pipeline itself (FR-006, FR-008, SC-001).
2. **Citations always resolvable.** Every `sources` entry in a returned result resolves to evidence actually
   retrieved during that same call (FR-009, SC-002).
3. **T-codes always verified.** Every `tcodes` entry is on the allow-list; anything else lands in
   `unverified_tcodes`, never silently in `tcodes` (FR-010, SC-003).
4. **Out-of-scope forced, not asked.** When Evidence is empty, `category` is `out_of_scope` with empty `tcodes`
   and `sources`, regardless of any model text (FR-011, FR-012, SC-004).
5. **Bounded loop.** `mode="agent"` never issues more than `MAX_STEPS` tool calls (FR-003, SC-005).
6. **No duplicate calls.** The same `(tool, normalized args)` pair is never dispatched twice within one call to
   `triage()` (FR-004, SC-006).
7. **Determinism (with the chat cache, R-09).** Identical `(log, mode, corpus_sha, chat_model)` with a warm cache
   yields an identical `TriageResult` — the basis of FR-020.
8. **No side effects.** No tool is anything but read-only; `triage()` never modifies the corpus, the index, or any
   external system (FR-013).

---

## Errors

| Exception | Raised when | CLI exit |
|---|---|---|
| `InvalidQueryError` | log empty, whitespace-only, or outside the 10–4000 character range (FR-015) — reuses Feature 1's `app.retrieval.search.InvalidQueryError` | 2 |
| `StaleIndexError` | the underlying `Store` (used by `search_runbook`) is stale or missing — reuses Feature 1's error as-is | 5 |
| `UpstreamError` | the gateway fails or times out during a chat or embedding call | 4 |
| `ConfigError` | required env var missing or malformed (e.g. no `CHAT_MODEL`/`OPENAI_API_KEY`) | 3 |

Exceptions are raised, never swallowed into a fabricated result — a gateway failure must surface as a gateway
failure, never as a low-confidence guess presented as if it came from real evidence (Constitution II).

---

## Repository and single-gateway seams

```
triage()                       service   ← CLI and eval both call only this
  ├── app.agent.loop            Phase 1 evidence-gathering (mode-dependent, R-08)
  │     └── app.agent.tools     search_runbook (wraps app.retrieval.search.search), lookup_tcode (wraps app.retrieval.runbooks.load_tcodes)
  ├── app.agent.formatter       Phase 2 draft + repair loop
  ├── app.agent.verify          citation / T-code / out_of_scope checks
  ├── app.agent.fallback        R-05 deterministic downgrade
  ├── app.normalize.*           pure functions, no I/O (reused from Feature 1, R-10)
  └── app.llm.chat()            the ONLY gateway caller for chat (Constitution VI); app.llm.embed() unchanged
```

`Store` is injectable (same as Feature 1's `search()`) so every test runs offline against a small fake corpus
with `app.llm.chat` mocked.

---

## Test obligations

Offline, with `app.llm.chat` mocked (Constitution VIII):

| Test | Asserts |
|---|---|
| `test_agent_loop.py` | `MAX_STEPS` termination forces a stop; natural stop (no tool call) ends the loop; repeated `(tool, args)` is never re-dispatched |
| `test_agent_formatter.py` | JSON extraction from fenced/prose-wrapped text; repair loop retries on structural failure; cap exhaustion routes to fallback |
| `test_agent_verify.py` | a citation not in Evidence is dropped; a T-code not on the allow-list lands in `unverified_tcodes`; `out_of_scope` forcing overrides the model's own category when Evidence is empty, and does not trigger on a multi-search case with at least one non-empty result |
| `test_agent_fallback.py` | the fallback result always passes `TriageResult` validation; `confidence == "low"`; `tcodes`/`sources`/`steps` all trace to the single source runbook |
| `test_triage_service.py` | end-to-end wiring for all three modes with `app.llm.chat` mocked; `InvalidQueryError` on a too-short log; the pipeline never raises from inside formatting/repair/verify |
| (search-level, reused) | citation resolvability, allow-list verification — same guarantees Feature 1's own `search()` contract already tests, now exercised through this service too |
