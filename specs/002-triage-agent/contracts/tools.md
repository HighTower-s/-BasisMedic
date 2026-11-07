# Contract: Agent Tools (`app/agent/tools.py`)

**Feature**: `002-triage-agent` | **Layer**: repository-adjacent orchestration

Both tools are **read-only** and **allow-listed** (Constitution IV literal text). Neither modifies the corpus,
the index, or any external system. Both accept and return plain strings/dicts — never raw Python exceptions — so
a malformed call from the model always comes back as a string the model can read and react to, per the course
material's "errors are strings too" pattern Feature 1's own design notes already follow.

```python
TOOLS: dict[str, Callable[[dict], str]] = {
    "search_runbook": search_runbook,
    "lookup_tcode": lookup_tcode,
}
```

A tool name not in `TOOLS` is never dispatched; the loop returns a string error ("unknown tool: ...") as the
tool-role message instead, so the model can self-correct (Constitution IV: "Tool calls MUST be allow-listed").

---

## `search_runbook`

Wraps Feature 1's `app.retrieval.search.search()` — no retrieval logic is duplicated here.

| Argument | Type | Validation |
|---|---|---|
| `query` | `str` | 10–300 characters after stripping; outside that range, the tool returns a string error, not a tool dispatch exception |

**Description shown to the model** (this text doubles as the model-facing prompt that shapes when it is called):
"Search the SAP Basis runbooks. Use the error code or message from the log as the query. Call again with a
different query if the results don't match."

**Return value** (always a string):

- On a non-empty result: a fenced, numbered listing of up to 3 hits, each showing its `doc_id#section` address
  and the section text — the same information Feature 1's CLI already prints for a human, reused for the model.
- On an empty result (Feature 1's `search()` returned `[]`): the literal string `NO_RELEVANT_RUNBOOK`.
- On a query outside the 10–300 character bound, or any other validation failure: a string naming the problem,
  never a crash.

**Side effect on the caller's state**: every call (success or `NO_RELEVANT_RUNBOOK`) is recorded as a
`ToolCallRecord` (data-model.md § 3); the `Hit`s from a non-empty result are appended to that request's Evidence
(R-11).

---

## `lookup_tcode`

Wraps Feature 1's `app.retrieval.runbooks.load_tcodes()` allow-list — no new T-code data source.

| Argument | Type | Validation |
|---|---|---|
| `code` | `str` | must match `^[A-Z][A-Z0-9_/]{1,19}$` (Feature 1's own `TCODE_RE`, reused); a non-matching string returns a string error, not a dispatch exception |

**Description shown to the model**: "Look up what an SAP transaction code is for. Only use this for codes that
appear in the runbook search results."

**Return value** (always a string):

- A matching code: its one-line description from `data/tcodes.json` (e.g. `"ST02: Tune Summary — buffers and
  memory"`).
- A code not on the allow-list: the literal string `unknown tcode`.
- A malformed code string: a string naming the format problem.

**Side effect on the caller's state**: recorded as a `ToolCallRecord`, but — unlike `search_runbook` — a
`lookup_tcode` call never contributes to Evidence; it is a lookup, not a source of citable text. This is
deliberate: a `sources` citation always means "a runbook section," never "a T-code lookup," keeping FR-009's
"evidence actually returned by `search_runbook`" literal.

---

## Argument validation order (both tools)

1. Parse the model's arguments (JSON-decode if the mechanism is native function-calling; pattern-match if the
   text-protocol fallback from R-02 is active).
2. If parsing fails: return a string error, never raise.
3. Validate against the table above.
4. If invalid: return a string error, never raise — and do **not** count as a dispatched call for the repeated-call
   guard (R-03), since nothing was actually executed.
5. Only a successfully parsed and validated call is dispatched, recorded as a `ToolCallRecord`, and checked
   against the repeated-call guard on its next occurrence.

---

## Test obligations

Offline (Constitution VIII), no model or gateway call needed for these:

| Test | Asserts |
|---|---|
| `test_agent_tools.py` | `search_runbook` query length bounds; `NO_RELEVANT_RUNBOOK` on an empty `search()` result; `lookup_tcode` code-shape validation; an unknown tool name is never dispatched; a malformed-argument call is never recorded as a `ToolCallRecord` (so it cannot be "repeated") |
