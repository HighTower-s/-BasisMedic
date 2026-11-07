# Phase 0 Research: Runbook Corpus, Labelled Eval Set, Measured Retrieval

**Feature**: `001-runbook-retrieval-eval` | **Date**: 2026-11-07

Each entry records a decision, why it was taken, and what was rejected. Items R-01 through R-05
resolve genuine gaps or contradictions found while reading the input plan against the spec; R-06
onward pin down details the spec left as "reasonable default".

---

## R-01 — Recall@3 and MRR are reported both pre-gate and post-gate

**Decision**: `run_retrieval.py` computes each retrieval metric twice per run: once over the ranked
list **before** the relevance gate is applied, once **after**. Experiment tables E1 (chunking) and E2
(retrieval mode) report pre-gate numbers. The headline test-set table and the E3 `MIN_SCORE` sweep
report post-gate numbers. Every table header states which it shows.

**Rationale**: these two numbers answer different questions and conflating them breaks Principle I.
Post-gate recall falls mechanically as `MIN_SCORE` rises, so if E1/E2 used post-gate numbers, a
chunking change and a gate change would be indistinguishable in the result — "one variable at a time"
would be violated silently. Conversely the sweep in E3 is *about* the gate, so it needs post-gate
recall to show the trade-off curve against out-of-scope rejection. Computing both costs one extra
tally in the same pass.

**Alternatives considered**: *pre-gate only* — leaves the author unable to state what the delivered
system actually retrieves, and makes the false-refusal rate unrelatable to recall. *Post-gate only* —
what the input plan implied; rejected because it entangles ranking quality with gate tuning and would
make E1/E2 uninterpretable.

**Status**: this was the open question from the interrupted `/speckit-clarify` session. Decided here
so planning could continue; it changes metric semantics only, not code structure, so it is cheap to
overrule.

---

## R-02 — The relevance gate is mode-specific, because BM25 mode has no cosine

**Decision**:

| Mode | Gate rule |
|---|---|
| `dense`, `hybrid` | Return `[]` when dense top-1 cosine `< MIN_SCORE` **and** no rare corpus token (R-03) appears in the query. |
| `bm25` | Return `[]` when no rare corpus token appears in the query. No score threshold. |

Results tables label the BM25 row as gated by the token rule alone.

**Rationale**: the input plan specifies gating on "the dense top-1 cosine", which is right for
dense/hybrid — RRF scores are not on a 0–1 scale, so they cannot carry a meaningful absolute floor.
But FR-017 and SC-012 require the BM25-only path to run with **no network access**, and in that mode
no cosine exists. Without a mode-specific rule, either the BM25 baseline cannot be evaluated offline
(breaking SC-012) or it silently calls the gateway (breaking FR-017). BM25 scores are unbounded and
corpus-dependent, so inventing a second tuned threshold would add a knob that Principle VI's
simplicity rule does not justify for a baseline whose purpose is ranking comparison, not gating.

**Consequence to report honestly**: R-BM25's out-of-scope rejection figure is produced by a weaker
gate than the final system's. The results table says so rather than presenting the numbers as
like-for-like (Principle II).

**Alternatives considered**: *a second env var `MIN_BM25_SCORE` swept on dev* — more faithful, but
doubles the gate surface and the sweep space for a baseline that is not shipped. *No gate at all in
BM25 mode* — would report 0% out-of-scope rejection for R-BM25, which is misleading in the other
direction since the token rule does real work there.

**Open to revision**: the spec and plan both treat this rule as a hypothesis. If the E3 dev sweep
shows the cosine+token rule does not separate in-scope from out-of-scope cases, the rule is replaced
and the replacement is reported with the evidence that motivated it.

---

## R-03 — "Rare corpus token" has a concrete, testable definition

**Decision**: a query token `t` is a *rare corpus token* when **both** hold:

1. `t` (lower-cased) is present in the BM25 vocabulary built from the corpus, and
2. `t` either matches `^[A-Z][A-Z0-9_]{5,}$` in its original casing (the shape of an ABAP runtime
   error, e.g. `TSV_TNEW_PAGE_ALLOC_FAILED`, `SYSTEM_NO_ROLL`) **or** is a key in `data/tcodes.json`
   (e.g. `SM37`, `ST22`).

Implemented as `bm25.rare_tokens(query) -> set[str]` and unit-tested directly.

**Rationale**: the input plan says "no BM25 token from the query matches a rare token (error
code/T-code) in the corpus" without defining rarity. Left undefined it is untestable, and an
undefined gate condition is the single most load-bearing rule in the feature (it decides when the
system refuses to answer). Condition 1 keeps the rule corpus-relative — a code we have no runbook for
does not qualify, which is exactly what makes the HANA and duplicate-key out-of-scope cases
rejectable. Condition 2 keeps it explainable in a demo without reference to corpus statistics.

**Alternatives considered**: *document-frequency threshold (token appears in ≤ 2 runbooks)* — more
principled information-retrieval-wise, but introduces a tuned integer, varies as the corpus grows,
and is harder to explain than a regex. Worth revisiting if the regex proves too narrow; the function
boundary makes that a one-function swap. *Any corpus-vocabulary overlap at all* — far too permissive;
common words like "job" or "user" appear in every out-of-scope log and would defeat the gate.

---

## R-04 — Index builds atomically into a temporary directory, then swaps

**Decision**: `ingest.build_index()` writes `chunks.jsonl`, `embeddings.npy`, and `manifest.json`
into `data/index.tmp/`, then replaces `data/index/` with it and removes the old directory. On any
failure the temporary directory is discarded and the previous index remains intact and usable.

**Rationale**: the input plan says "rebuilt from scratch each ingest (delete old first)", which
satisfies FR-009's requirement that no stale content survive, but is not crash-safe. The build's
expensive middle step is ~96 embedding calls to the gateway; a timeout or a 500 there would, under
delete-first, leave the author with **no** index at all — during a live demo, after a one-character
runbook edit. Building aside and swapping gives FR-009's guarantee (the swapped-in directory contains
only current content) without that failure mode.

**Alternatives considered**: *delete-first as specified* — simplest, rejected for the reason above.
*Versioned index directories with a `current` symlink* — robust but needs symlink handling on Windows
(where the author works) and adds cleanup logic for no gain at this scale.

---

## R-05 — Thai queries contribute nothing to BM25; hybrid must tolerate an empty sparse list

**Decision**: keep the tokenizer as `[A-Za-z0-9_/]+`, lower-cased. Accept that Thai text yields zero
tokens and therefore a zero-length BM25 result for the three Thai test cases and the Thai dev case.
`fuse_rrf(dense_ranked, bm25_ranked)` must be correct when either list is empty, with a unit test for
that case. `results.md` reports the Thai slice separately so the effect is visible.

**Rationale**: Thai is written without inter-word spaces, so a character-class tokenizer cannot
segment it — every Thai case is carried entirely by `bge-m3`'s multilingual embedding. This is worth
planning for explicitly rather than discovering during E2: it predicts that the Thai slice will show
dense ≈ hybrid > bm25 ≈ 0, and it means an empty BM25 list is a *normal* input to fusion, not an edge
case. Principle II makes this a finding to report, not a defect to paper over.

**Alternatives considered**: *add a Thai segmenter (`pythainlp`)* — a new dependency, outside the
course stack, to improve a baseline (BM25) that is not the shipped configuration; rejected under
Principle VI and VII. *Drop the Thai cases* — rejected: cross-language retrieval is a genuine measured
question (spec Assumptions) and dropping inconvenient cases is precisely what Principle II forbids.

---

## R-06 — Index identity and staleness come from one corpus hash

**Decision**: `manifest.json` records `corpus_sha` = SHA-256 over the concatenated bytes of
`data/runbooks/*.md` and `data/tcodes.json` in sorted filename order, plus `chunk_strategy`,
`embed_model`, `embed_dim`, `n_runbooks`, `n_chunks`, `built_at`, and `git_commit`. `store.load()`
recomputes the corpus hash and raises `StaleIndexError` naming the fix (`python -m app.cli ingest`)
when it differs. Every eval results file copies `corpus_sha` and `git_commit` from the manifest.

**Rationale**: this one value answers three separate spec requirements at once — FR-020 (stale-index
detection), FR-035 (results record the corpus version measured), and the reproducibility claim in
SC-004. It is also the honest answer to "which corpus produced this number", which a timestamp or a
hand-maintained version string is not.

**Alternatives considered**: *mtime comparison* — breaks on checkout, which rewrites mtimes and would
either cry stale constantly or miss a real edit. *Git commit alone* — wrong for uncommitted edits,
which is the normal state while writing runbooks. *A manual `corpus_version` field* — guaranteed to
drift the first time the author forgets to bump it.

**Hard failure rather than a warning**: scoring an eval run against text that is no longer in the
corpus produces a number the repository cannot reproduce. That is the dishonest-number failure mode
Principle II exists to prevent, so it fails the run rather than printing a warning the author may
scroll past.

---

## R-07 — De-duplication to distinct documents lives in `search()`, for every caller

**Decision**: `search()` always collapses results to the best-scoring chunk per `doc_id` before
applying `k`. The CLI and the eval harness therefore see identical behaviour.

**Rationale**: the input plan says results are "collapsed to distinct docs **for eval**", but FR-015
states the guarantee for every search, and SC-005's "3 results mean 3 candidate answers" property is
what makes top-3 meaningful to a human pasting a log. Putting the collapse in the service keeps
Constitution VI's single service path real — if the harness and the CLI de-duplicated differently,
the measured system would not be the demonstrated system.

**Alternatives considered**: *collapse in the eval harness only* — as the input plan implied;
rejected because it means the reported recall@3 describes a code path the CLI never runs.

---

## R-08 — Metric population boundaries are fixed in code, not per-run judgement

**Decision**: `eval/schema.py` derives the populations once from the case labels:

- *in-scope* = cases with non-empty `gold_docs` → 26 test cases (24 single + 2 mixed), 8 dev cases.
  Basis for recall@3, MRR, false-refusal rate.
- *out-of-scope* = cases with `gold_category == "out_of_scope"` and empty `gold_docs` → 4 test, 2 dev.
  Basis for gate accuracy.
- recall@3 and MRR collapse retrieved chunks to `doc_id` before ranking (spec Assumptions).
- `acceptable_docs` never earn recall credit and never create a failure record (FR-034).

**Rationale**: these are spec assumptions; writing them as derived properties with a validator test
stops each experiment from re-deciding its own denominator, which is how result tables stop being
comparable.

**Alternatives considered**: *mixed cases as their own population* — reduces the in-scope denominator
to 24 and makes the mixed slice too small (n=2) to read; they stay in-scope and are *also* reported as
a slice.

---

## R-09 — Embedding cache keyed by content, giving run-to-run determinism

**Decision**: `app/llm.py` wraps `embeddings.create` with a disk cache at `data/cache/`, key
`sha256(f"{model}|{text}")`, value the raw float vector. Cache hits never call the gateway.
`data/cache/` is git-ignored. `embed()` preserves input order (`data[i] ↔ input[i]`), batches
requests, and asserts `len(vector) == 1024`.

**Rationale**: FR-036/SC-004 demand identical metrics across consecutive runs; `run_all.py` embeds the
same corpus and the same 40 query logs across ~6 configurations. Content-keyed caching makes repeats
both free and bit-identical, and removes dependence on upstream determinism the project does not
control. Order preservation and the dimension assertion are the two failure modes that corrupt an
embedding index silently.

**Deliberate divergence from the reference notes**: `docs/prepare/09_eval_plan.md` § 6 specifies
`key = sha1 of the text`. This decision uses `sha256` and includes the **model name** in the key.
Model-scoping is the substantive change: a text-only key would silently serve `bge-m3` vectors if
`EMBED_MODEL` ever changed, corrupting an index with no visible symptom. SHA-256 over SHA-1 is
incidental.

**Alternatives considered**: *no cache* — gateway calls on every experiment and a reproducibility
claim resting on upstream stability. *In-memory cache only* — does not survive between configurations
if they run as separate processes. *Committing the cache* — would make the repo reproducible without
the gateway, but bloats history with binary blobs; committing `data/index/` instead is the better
version of that idea, and `docs/prepare/templates/gitignore.txt` leaves it open as a choice (T004).

---

## R-10 — Query validation bounds, fixed and shared with the future `TriageRequest`

**Decision**: two distinct limits, because they do different jobs.

| Limit | Value | Behaviour |
|---|---|---|
| Accepted input length | 10–4000 characters | below 10 or whitespace-only → `InvalidQueryError`; above 4000 → rejected at the edge |
| Query length after normalisation | ≤ 2000 characters | `normalize.cap_length(text, limit=2000)` truncates, and the truncation is announced |

**Rationale**: FR-019 requires rejection below "the minimum accepted length" without fixing a number.
10 and 4000 come from the author's planned `TriageRequest` bounds in `docs/prepare/02_design.md`
§3.1, so Feature 2's API edge and this feature's CLI share one rule instead of disagreeing. The 2000
figure comes from `docs/prepare/04_system_flow.md` § B2 ("ตัดเหลือ ≤ 2,000 ตัวอักษรส่วนสำคัญ") and is a
*different* limit: what gets embedded as the query, after noise stripping. Keeping them separate is
what lets a full 4000-character ST22 dump be accepted and still searched, satisfying the spec's
"very long log" edge case, without sending 4000 characters of timestamps to the embedding model.

**Correction**: an earlier draft of this decision conflated the two as a single 4000-character
`cap_length`, which contradicted `04_system_flow.md` § B2.

**Alternatives considered**: *reject over-long queries outright* — would fail the spec's "very long
log" edge case. *One limit for both* — what the earlier draft did; it either rejects legitimate dumps
or embeds mostly noise.

---

## R-11 — Results artifacts accumulate per configuration; `results.md` is generated

**Decision**: `run_retrieval.py` writes `eval/results/{experiment}_{config_slug}.json` — one file per
(experiment, configuration, split) — containing the full config block (mode, chunk strategy, `k`,
`min_score`, `corpus_sha`, `git_commit`, `embed_model`), per-case outcomes, and both pre- and post-gate
aggregates. Failures append to `eval/results/failures.jsonl`, truncated at the start of each
`run_all.py` invocation and always created. `eval/results/results.md` is regenerated wholesale from
those json files and is never hand-edited. All of `eval/results/` is committed.

**Rationale**: FR-037's before/after comparison requires both sides to still exist as artifacts, and
Principle I requires results committed *with their config*. A single overwritten results file cannot
support either. Generating `results.md` from the json files rather than typing it is what makes
Principle II's "never inflate" structurally true rather than a promise.

**Alternatives considered**: *one overwritten `results.json`* — loses the baseline the moment the next
configuration runs. *Timestamped run directories* — defensible, but `Date.now()`-style naming makes
diffs noisy and the config slug is the identity that actually matters.

---

## R-12 — Task ordering is the mechanism that enforces Evaluation-First

**Decision**: implementation proceeds in this order, each step a separate commit:

1. `pyproject.toml`, `.env.example`, `.gitignore`, `app/config.py` — project skeleton.
2. `data/tcodes.json` + 16 `data/runbooks/*.md` + `app/retrieval/runbooks.py` + parser tests.
3. `eval/cases_dev.jsonl`, `eval/cases_test.jsonl`, `eval/schema.py` + validator tests — **before any
   retrieval code exists**.
4. `eval/metrics.py` + hand-computed metric tests.
5. `app/normalize.py`, `app/retrieval/chunk.py`, `bm25.py` + tests — still no network.
6. `store.py`, `search.py` in `bm25` mode, `app/cli.py`, `eval/run_retrieval.py` → **first real
   recall@3 number, produced offline**.
7. `app/llm.py` + cache, `ingest.py` + manifest → `dense` mode.
8. RRF fusion → `hybrid` mode; gate rule per R-02/R-03.
9. `eval/run_all.py` → E1, E2, E3; `results.md`; failures; Limitations block.

**Rationale**: Principle I is not satisfiable by intent — it is satisfied by `git log` showing the
eval set committed before `search.py`. Step 6 is the checkpoint that matters: a real metric from the
test set before a single embedding is computed, which is also what makes US2 independently testable
(SC-012) and de-risks the gateway being unavailable on the day.

**Alternatives considered**: *build retrieval first, then eval* — the natural engineering instinct and
exactly what the constitution forbids; it produces an eval set shaped to flatter the retriever that
already exists.

---

## Resolved unknowns

No `NEEDS CLARIFICATION` markers remain. For the record, these were the questions queued in the
interrupted clarify session and where each landed:

| Queued question | Landed in |
|---|---|
| Recall measured pre- or post-gate? | R-01 (decided: both, labelled) |
| What happens if the build fails mid-embed? | R-04 (atomic tmp-dir swap) |
| How is "corpus version" identified / staleness detected? | R-06 (`corpus_sha` in manifest) |
| Are results artifacts retained per run or overwritten? | R-11 (per-config files, generated `results.md`) |
| What is the minimum query length? | R-10 (accept 10–4000 chars; normalise to ≤ 2000) |
