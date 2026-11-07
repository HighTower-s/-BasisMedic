# Quickstart & Validation: Runbook Corpus, Eval Set, Measured Retrieval

**Feature**: `001-runbook-retrieval-eval` | **Date**: 2026-11-07

The path a newcomer follows to prove this feature works, and the rehearsal for the README that
Constitution IX requires. Each step states its expected observable outcome and the success criterion
it demonstrates. No implementation code here — see [contracts/](./contracts/) and
[data-model.md](./data-model.md).

**Prerequisites**: Python 3.12, `uv`, a course gateway API key. Steps 0–4 need **no network**.

---

## 0. Install

```bash
uv sync
cp .env.example .env       # Windows: copy .env.example .env
```

Leave `OPENAI_API_KEY` as-is for now — steps 1–4 never call out.

**Expected**: `uv sync` resolves `openai`, `numpy`, `rank-bm25`, `pydantic`, and `pytest` from
`uv.lock`. No key is needed yet, which is itself the point of step 4.

---

## 1. Validate the corpus and the allow-list

```bash
uv run pytest tests/test_runbooks.py -q
```

**Expected**: passes. Asserts 16 runbooks, 2 per category across the 8 categories; unique `doc_id`s;
exactly the six sections in order; at least one reference URL each; and every T-code named in the
corpus present in `data/tcodes.json`.

→ **SC-006** (all corpus T-codes allow-listed), **FR-001/002/003/004/007**.

Break it on purpose to see the failure mode: add `ZZZZ` to any runbook's `tcodes` and re-run. The
test must fail naming the file and `ZZZZ` — not fail vaguely, and not pass.

---

## 2. Validate the evaluation set

```bash
uv run pytest tests/test_eval_cases.py -q
```

**Expected**: passes. Asserts exactly 10 dev and 30 test cases; the test split's 24 in-scope cases as
3 per category across easy/medium/hard, plus 4 out-of-scope and 2 mixed; exactly 3 Thai hard cases;
every one of the 16 runbooks the expected answer of at least one test case; no log duplicated across
splits; and **no case log sharing a contiguous 8-word span with any runbook section**.

→ **SC-001** (counts and distribution), **SC-002** (full runbook coverage), **SC-003** (no copied
phrasing), **FR-022 through FR-030**.

That last check is the one worth watching. It is what stops keyword retrieval from being flattered by
logs that quote the runbooks, which would make every number in the report meaningless.

---

## 3. Run the full offline test suite

```bash
uv run pytest -q
```

**Expected**: all tests pass with no network. Covers both chunkers, the BM25 tokenizer (including
Thai yielding zero tokens), RRF fusion with an empty input list, all four gate branches, the four
metric functions against hand-computed fixtures, `normalize`, store line/row alignment, the
stale-index check, the dev-only sweep guard, and the assertion that nothing in `app/retrieval/` or
`eval/` imports `app.cli`.

→ **Constitution VIII** (deterministic parts unit-tested with the gateway mocked).

---

## 4. Measure retrieval with no gateway at all

This is the checkpoint that matters most, and it comes before any embedding exists.

```bash
uv run python -m app.cli ingest --strategy section --no-embed    # chunks + BM25 only; no gateway calls
uv run python -m eval.run_retrieval --split test --mode bm25 --strategy section --min-score 0.40 --name R-BM25 --experiment E0
```

**Expected**: a complete results file at `eval/results/E0_bm25-section-k3-ms40_test.json` with real
recall@3, MRR, out-of-scope gate accuracy, and false-refusal rate, plus a per-case breakdown and the
config block including `corpus_sha` and the git commit. The numbers may be poor — the harness is what
is being validated.

→ **SC-012** (eval runs with no network), **SC-004** (one command, config recorded), **FR-017**,
**FR-031/032/035**, and **US2's independent test**.

Then prove determinism:

```bash
uv run python -m eval.run_retrieval --split test --mode bm25 --strategy section --min-score 0.40 --name R-BM25 --experiment E0
```

**Expected**: identical metrics. → **FR-036**, **SC-004**.

---

## 5. Build the real index

Set `OPENAI_API_KEY` in `.env` first.

```bash
uv run python -m app.cli ingest --strategy section
```

**Expected** (FR-012 — a partial build must be visible):

```
corpus      : 16 runbooks, 8 categories, 96 sections
tcodes      : 41 allow-listed
strategy    : section
embeddings  : 96 vectors, dim 1024  (cache: 0 hit, 96 miss)
index       : data/index/  corpus_sha=3f9a1c2e…  commit=37eb1df
```

Run it again. **Expected**: `cache: 96 hit, 0 miss`, same `corpus_sha`, and byte-identical
`chunks.jsonl` and `embeddings.npy`.

→ **SC-007** (rebuild is clean and identical), **FR-008/009**, **R-04** (atomic swap), **R-09** (cache).

Delete a runbook, re-ingest, and confirm zero traces of it remain in `chunks.jsonl` — then restore it.
→ **SC-007**, **FR-009**.

---

## 6. Search a log, and get refused on one that isn't covered

Use a **log**, not a runbook. Searching runbook text would echo the corpus back at itself and prove
nothing — it is the same self-flattery FR-029 and SC-003 forbid in the eval set.

```bash
uv run python -m app.cli search "Runtime Errors         TSV_TNEW_PAGE_ALLOC_FAILED
Short Text             No more storage space available for extending an internal table.
Program                ZFI_MONTHLY_REPORT
User and Transaction   Client 100, User BATCH_FI, background job ZFI_MONTHLY"
```

**Expected**: up to 3 hits, best first, each printing a `doc_id#section` address, the score the active
mode ranked by, the category, and a text snippet. The top hit should be `mem_tsv_tnew_page_alloc`.
Every address resolves in the corpus.

→ **SC-005** (resolvable citations), **FR-013/014/015**.

Now the refusal:

```bash
uv run python -m app.cli search "HANA alert 2: Log volume /hana/log/HDB is 98% full. Log backups failing since 04:00."
```

**Expected**: `NO_RELEVANT_RUNBOOK`, zero hits, the best dense score and the rare tokens seen, exit
code **0** — a correct refusal is a success, not an error.

→ **SC-008** (out-of-scope returns exactly zero results), **FR-018**, **Constitution III**.

Three more worth running by hand:

```bash
uv run python -m app.cli search "  "                        # expect exit 2, clear message
uv run python -m app.cli search --min-score 0.95 "Runtime Errors  TIME_OUT
Short Text  Time limit exceeded."                           # expect the same or fewer hits
uv run python -m app.cli search --mode dense "…"            # against a --no-embed index: exit 5
```

**Note on the 0.95 example**: `TIME_OUT` is itself a rare token (research.md R-03 shape), so it can
rescue a result even at a very high floor — that is the gate working as designed (an exact error
code should not be refused just because embedding similarity is diluted by noise), not a violation
of monotonicity. Monotonicity (FR-018, US3-3) means raising the floor never *increases* the result
count for a fixed query — it does not promise zero results exist at every high floor.

→ **FR-019** (invalid query rejected), **FR-018** + US3-3 (floor monotonicity), and the no-silent-
downgrade rule from contracts/cli.md.

Once `examples/` exists (T084), the same checks read better as
`uv run python -m app.cli search --file examples/tsv_dump.log`.

---

## 7. Detect a stale index

```bash
# edit any runbook's Symptoms section, then:
uv run python -m app.cli search "TIME_OUT Time limit exceeded in dialog work process"
```

**Expected**: `StaleIndexError`, exit code 5, message naming `python -m app.cli ingest` as the fix.
Not stale text silently returned.

→ **FR-020**, **R-06**. Re-ingest to continue.

---

## 8. Reproduce every reported number with one command

```bash
uv run python -m eval.run_all
```

**Expected**: E1, E2, then E3 in order, writing one json per configuration, `failures.jsonl`, and
`eval/results/results.md` containing:

- E1 chunking — `fixed-800/150` vs `section`, pre-gate, variable named
- E2 mode — `bm25` / `dense` / `hybrid`, pre-gate, R-BM25 and R-Dense-naive marked as baselines
- E3 sweep — dev only, 0.30→0.60 step 0.05, post-gate recall against out-of-scope rejection, with the
  chosen `MIN_SCORE` and the run it came from
- headline test table — post-gate, with the BM25 row flagged as gated by the token rule alone
- per-difficulty slices including the Thai and mixed rows
- a verdict sentence, stated plainly whether or not hybrid wins
- a Limitations block

→ **SC-004**, **SC-009/010/011/014**, **FR-031/037/038/039/040/042/043/044**, **Constitution I & II**.

Run it twice. **Expected**: identical retrieval metrics. → **FR-036**, **SC-004**.

Confirm the dev-only guard holds:

```bash
uv run pytest tests/test_sweep_guard.py -q
```

**Expected**: passes — `sweep_min_score("test")` raises. → **FR-041**, **SC-009**.

---

## 9. Check the search is fast enough to iterate with

```bash
uv run python -m app.cli search --mode hybrid --file examples/tsv_dump.log   # time it
```

**Expected**: under 3 seconds wall-clock, dominated by the single query-embedding round trip. BM25
mode should be well under a second. → **SC-013**.

---

## Done when

| # | Check | Criteria |
|---|---|---|
| 1 | Corpus and allow-list valid | SC-006 |
| 2 | Eval set valid, covering, and not copied from the runbooks | SC-001, SC-002, SC-003 |
| 3 | Full suite green offline | Constitution VIII |
| 4 | Real recall@3 with no network, repeatable | SC-012, SC-004 |
| 5 | Index builds clean and identical; survives a failed build | SC-007 |
| 6 | Cited hits, and an explicit refusal on an uncovered log | SC-005, SC-008 |
| 7 | Stale index refused, not silently served | FR-020 |
| 8 | `run_all` reproduces every reported number, honestly | SC-004, SC-009–011, SC-014 |
| 9 | Search under 3 s | SC-013 |

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| exit 5, `StaleIndexError` | corpus edited after the last build | `python -m app.cli ingest` |
| exit 3, `ConfigError` | `.env` missing or a variable malformed | copy `.env.example`, fill the key |
| exit 4, `UpstreamError` | gateway down, wrong base URL, or bad key | verify the base URL against the course profile page; `--mode bm25` works offline meanwhile |
| exit 2 on `ingest` | a runbook violates the format, or names a T-code outside the allow-list | the message names the file and value |
| `cache: 0 hit` on a rebuild | `data/cache/` was cleared, or the chunk text changed | expected after a corpus edit; otherwise check `EMBED_MODEL` |
| Thai case retrieves nothing in `bm25` mode | expected — the tokenizer drops Thai entirely | a measured finding, not a bug (R-05); compare the `dense` row |
