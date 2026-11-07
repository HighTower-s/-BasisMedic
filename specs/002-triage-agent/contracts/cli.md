# Contract: CLI `triage` subcommand (`app/cli.py`)

**Feature**: `002-triage-agent` | **Layer**: edge

Extends Feature 1's `app/cli.py` (which already has `ingest` and `search`) with a third subcommand. Same rule as
Feature 1's contract: this edge parses arguments, calls one service function, formats output, and maps exceptions
to exit codes — no business logic of its own (Constitution VI).

---

## `python -m app.cli triage`

Runs the full agent on a pasted log (FR-001).

```
uv run python -m app.cli triage "<log text>"
uv run python -m app.cli triage --file path/to/sample.log
      [--json] [--show-trace]
```

| Argument | Default | Meaning |
|---|---|---|
| positional / `--file` | — | exactly one required; `--file` reads UTF-8, same convention as Feature 1's `search` subcommand |
| `--json` | off | emit the `TriageResult` as JSON for scripting |
| `--show-trace` | off | print each tool call made during Phase 1 (tool name, arguments, truncated result) to stderr — how a surprising answer gets diagnosed, mirroring `search`'s `--show-tokens` |

This subcommand always runs `mode="agent"` (the full loop) — `E-NoRAG`/`E-ClassicRAG` are evaluation-only
baselines, never exposed as a CLI mode a user could accidentally invoke expecting the real system's behaviour.

**Human output** — the full `TriageResult`, printed legibly:

```
category    : memory_dump
summary     : TSV_TNEW_PAGE_ALLOC_FAILED short dump during a background job; internal table exceeded memory
tcodes      : ST22, ST02
steps       :
  1. Open ST22 and read "Error analysis" for requested vs. used memory size.  [ST22]
  2. Open ST02 and check extended/heap memory usage around the dump time.    [ST02]
escalate_to : developer
sources     : mem_tsv_tnew_page_alloc#check, mem_tsv_tnew_page_alloc#cause
confidence  : high
```

**Out-of-scope output** — mirrors Feature 1's `NO_RELEVANT_RUNBOOK` refusal shape, exit code **0** (a correct
refusal is a success, not an error — same rule as Feature 1's `search` contract):

```
category    : out_of_scope
summary     : no runbook section cleared the relevance floor for this log
tcodes      : (none)
steps       :
  1. Not covered by the runbooks; investigate manually or escalate.
sources     : (none)
confidence  : low
This incident is not covered by the runbooks.
```

`--show-trace` additionally prints every tool call made, which is how a surprising `out_of_scope` or an
unexpected fallback gets diagnosed during a demo — the same role Feature 1's `--show-tokens` plays for `search`.

**Fallback output** — identical shape to a normal result, with `confidence: low` and a trailing note naming that
repair was exhausted and the result was built from the top retrieved runbook only (so the degraded path is never
silently indistinguishable from a normal high-confidence answer).

---

## Exit codes

| Code | Condition |
|---|---|
| 0 | a result was returned — including a correct `out_of_scope` refusal and a low-confidence fallback |
| 2 | invalid log — `InvalidQueryError`: empty, whitespace-only, or outside 10–4000 characters (FR-015) |
| 3 | config missing/invalid — e.g. no `OPENAI_API_KEY` or `CHAT_MODEL` |
| 4 | gateway failure — `UpstreamError` during a chat or embedding call |
| 5 | no index, or index stale against the corpus — `StaleIndexError`, same as Feature 1's `search` subcommand |

---

## Cross-cutting rules

1. **No business logic.** The command body is: parse args → call `app.triage_service.triage()` → format → map
   exception to exit code. Anything else belongs in `app/triage_service.py` or `app/agent/`.
2. **Nothing imports the CLI.** `app/agent/*`, `app/triage_service.py`, and `eval/*` must never import `app.cli` —
   extends Feature 1's existing `tests/test_cli_boundary.py` assertion to cover the new modules (Constitution VI).
3. **Errors to stderr, results to stdout**, so `--json` output stays pipeable — same rule as `search`.
4. **No secrets in output.** Never echoes `OPENAI_API_KEY`, same as `ingest`/`search`.
5. **Always available as the demo fallback** (Constitution VI): the CLI's `triage` subcommand must keep working
   once Feature 3's API/UI exist later — this feature does not and must not make the CLI depend on either.

---

## Evaluation entry point

Not part of `app/cli.py`, mirroring Feature 1's `eval/run_retrieval.py` convention:

```
uv run python -m eval.run_e2e --split {dev,test} --mode {agent,E-NoRAG,E-ClassicRAG} --name …
```

`eval/run_all.py` is extended to run all three modes over the test split as experiment E4 and append the
comparison table to `results.md` (FR-016, FR-018, FR-022) — it accepts no tuning arguments, same discipline as
Feature 1's `run_all.py`.
