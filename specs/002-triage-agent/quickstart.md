# Quickstart & Validation: Triage Agent

**Feature**: `002-triage-agent` | **Date**: 2026-11-08

The path a newcomer follows to prove this feature works, and the rehearsal for the README section Constitution
IX requires. Each step states its expected observable outcome and the success criterion it demonstrates. Builds
directly on Feature 1's quickstart — steps 0–7 there (corpus, eval set, index, retrieval) are prerequisites and
are not repeated here.

**Prerequisites**: Feature 1's quickstart already completed (`data/index/` built with embeddings, `OPENAI_API_KEY`
set). `CHAT_MODEL` is already in `.env` from Feature 1's `.env.example` (`gemma-4-E4B-it`), unused until now.

---

## 0. Offline tests pass with no network

```bash
uv run pytest -q
```

**Expected**: every test from Feature 1 still passes, plus this feature's new tests (`test_agent_tools.py`,
`test_agent_loop.py`, `test_agent_formatter.py`, `test_agent_verify.py`, `test_agent_fallback.py`,
`test_triage_service.py`, `test_e2e_metrics.py`, `test_llm_chat_cache.py`) — all with `app.llm.chat` mocked, no
network.

→ **Constitution VIII**.

---

## 1. Triage a known in-scope log

```bash
uv run python -m app.cli triage --file examples/tsv_dump.log --show-trace
```

**Expected**: at least one `search_runbook` call shown in the trace (stderr); a result on stdout with
`category: memory_dump` and transaction codes drawn from `mem_tsv_tnew_page_alloc`'s own front-matter. If
`sources` is non-empty, every entry resolves to a section of that same runbook — verified by code
(`verify_citations`), never just asserted. **Note from a live run**: on `gemma-4-E4B-it`, the model frequently omits `sources` even when it clearly
used the retrieved evidence (visible in the trace) — this is a real, measured model-citation-discipline
gap, not a bug in `verify_citations` (which correctly drops anything *fabricated*, but cannot invent a
citation the model never attempted, and does not currently flag an *omitted* citation as unverified —
E4's `unverified_claim_rate` counts dropped/flagged claims, not missing ones). Worth naming in the
Limitations section rather than treated as a solved problem.

→ **User Story 1**, SC-002 (citations resolvable), SC-003 (T-codes verified).

---

## 2. Triage a log the corpus does not cover — explicit refusal, not a guess

```bash
uv run python -m app.cli triage --file examples/hana_disk_full.log --show-trace
```

**Expected**: `category: out_of_scope`, zero transaction codes, zero sources, exit code **0**. The trace shows at
least one `search_runbook` call that returned `NO_RELEVANT_RUNBOOK`.

→ **User Story 2**, SC-004.

---

## 3. Force the repair-and-fallback path

There is no CLI flag for this — it is a unit-test-level guarantee, not something to reproduce by hand against the
real gateway (the model may simply not fail on demand). Confirm it directly:

```bash
uv run pytest tests/test_agent_formatter.py tests/test_agent_fallback.py -q
```

**Expected**: passes — a forced structural-validation failure (mocked model response) triggers the bounded repair
loop, and exhausting it produces a fallback result that itself passes `TriageResult` validation with
`confidence: low`.

→ **User Story 3**, SC-001.

---

## 4. Confirm the repeated-call guard and the step bound

```bash
uv run pytest tests/test_agent_loop.py -q
```

**Expected**: passes — asserts a mocked model issuing the same tool call twice only results in one real
dispatch, and a mocked model that never stops calling tools is cut off at `MAX_STEPS`.

→ SC-005, SC-006.

---

## 5. Reproduce every end-to-end number with one command

```bash
uv run python -m eval.run_all
```

**Expected**: in addition to Feature 1's E1/E2/E3 output, this now also runs E4 (full agent vs. `E-NoRAG` vs.
`E-ClassicRAG` on the test split) and appends its section to `eval/results/results.md`: category accuracy,
T-code recall, unverified-claim rate, and valid-output rate for all three rows, each stating whether the agent
beat that baseline.

→ **User Story 4**, SC-007, SC-008.

Run it twice. **Expected**: identical verification-level outcomes (same category, same T-codes, same citations
per case) thanks to the chat cache (R-09) — numeric metrics therefore match exactly too.

→ FR-020, SC-007.

---

## 6. Confirm unverifiable claims are actually caught, not just assumed caught

```bash
uv run pytest tests/test_agent_verify.py -q
```

**Expected**: passes — a mocked model response citing a `chunk_id` never returned by `search_runbook` during that
run has that citation stripped before the result is returned; a mocked response naming a transaction code outside
the allow-list has it moved to `unverified_tcodes`, never left in `tcodes`.

→ **User Story 5**, SC-002, SC-003.

---

## 7. Check the failures list explains what went wrong

```bash
cat eval/results/failures.jsonl | tail -5
```

**Expected**: entries with `config_name` of `"agent"`, `"E-NoRAG"`, or `"E-ClassicRAG"` alongside Feature 1's own
retrieval-level entries, each with `expected_category`/`produced_category`, `expected_tcodes`/`produced_tcodes`,
and one of the six `FailureTypeE2E` values.

→ SC-009.

---

## 8. Confirm a mixed two-problem log is handled, not hidden

```bash
uv run python -m app.cli triage --file examples/mixed_lock_update.log --show-trace
```

**Expected**: a structurally valid single-category result (the schema cannot express two categories at once —
this is the known, spec-documented limitation, not a crash). If this case is in the committed test set, its
outcome also appears in `eval/results/failures.jsonl` labelled honestly rather than silently scored as a clean
pass.

→ SC-010.

---

## Done when

| # | Check | Criteria |
|---|---|---|
| 0 | Full offline suite green, including new agent tests | Constitution VIII |
| 1 | In-scope log → cited, verified result | SC-002, SC-003 |
| 2 | Out-of-scope log → forced refusal, not a guess | SC-004 |
| 3 | Repair + fallback path never produces an invalid result | SC-001 |
| 4 | Loop bound and repeated-call guard both enforced | SC-005, SC-006 |
| 5 | `run_all` reproduces every e2e number, twice, identically | SC-007, FR-020 |
| 6 | Unverifiable claims are actually caught by code | SC-002, SC-003 |
| 7 | Failures list explains every wrong/fallback/unverified case | SC-009 |
| 8 | Mixed-problem log handled and honestly reported | SC-010 |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Phase 1 never calls a tool, answers directly | native tool-calling not reliably triggered on `gemma-4-E4B-it` | switch the dispatch adapter to the R-02 text-protocol fallback; no change needed elsewhere |
| Every in-scope case falls back (`confidence: low`) | formatter JSON consistently malformed | check the Phase 2 prompt still excludes `tools=`; re-verify against `docs/prepare/02_design.md` § 5.3's exact failure mode |
| `run_all` numbers change between runs | `data/chat_cache/` was cleared, or `CHAT_MODEL`/temperature changed | expected after a cache clear; otherwise check the cache key inputs (R-09) |
| `unverified_claim_rate` is always 0.0 for every baseline | `verify.py` is not being applied identically to baselines | re-check R-08 — every mode must pass through the same `verify_citations`/`verify_tcodes` |
| exit 5, `StaleIndexError` on `triage` | same as Feature 1's `search` — corpus edited since the last `ingest` | `python -m app.cli ingest` |
