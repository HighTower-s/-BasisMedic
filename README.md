# BasisMedic

A measured, evaluated RAG + agent system that triages SAP Basis incidents. Paste an error log and
get back a validated structured result — incident category, transaction codes to open in order,
step-by-step checks, and citations — or an explicit "nothing relevant" refusal. Every citation and
every T-code is verified by code against real evidence, never trusted from the model. This
repository covers Features 1 and 2 of 3 for a university capstone project (*Building LLM-Powered
Applications*):

- **Feature 1** — the runbook corpus, the labelled evaluation set, and measured hybrid retrieval
  (`search()`).
- **Feature 2** — the triage agent: a bounded tool-calling loop built on top of `search()`,
  producing a verified structured `TriageResult`, measured end-to-end against named baselines.

Feature 3 (an HTTP API and web UI) has not started.

## Why

A triage assistant that is confidently wrong is worse than one that says "I don't know" — a
plausible-sounding but wrong T-code sequence, acted on at 2am, is the worst possible output. This
feature exists to prove the retrieval underneath that assistant actually works, honestly measured
against named baselines, before any language model ever touches the data. See
[`.specify/memory/constitution.md`](.specify/memory/constitution.md) for the full governing
principles (Evaluation-First, Honest Reporting, Grounded Answers Only).

## Setup

```bash
uv sync
cp .env.example .env        # Windows: copy .env.example .env
# fill in OPENAI_API_KEY for dense/hybrid search; bm25 mode needs no key at all
```

## Build the index

```bash
uv run python -m app.cli ingest --strategy fixed     # with embeddings (needs OPENAI_API_KEY)
uv run python -m app.cli ingest --strategy fixed --no-embed   # bm25-only, no network
```

Rebuilding is atomic — a failed build (e.g. gateway down mid-embed) leaves the previous index
intact. Embeddings are cached on disk (`data/cache/`, git-ignored) keyed by content, so a rebuild
with no corpus changes costs zero gateway calls.

## Search

```bash
uv run python -m app.cli search --file examples/tsv_dump.log --mode hybrid
uv run python -m app.cli search "paste a log or free-text description here"
uv run python -m app.cli search --file examples/hana_disk_full.log --mode hybrid   # explicit refusal
```

`--mode` is `bm25` (no network), `dense`, or `hybrid` (default). A result that clears the
relevance floor returns up to 3 hits, each with a `doc_id#section` address that resolves to real
corpus text. A log the corpus does not cover returns `NO_RELEVANT_RUNBOOK` with exit code 0 — a
correct refusal is a success, not an error.

## Triage (Feature 2)

```bash
uv run python -m app.cli triage --file examples/tsv_dump.log --show-trace
uv run python -m app.cli triage "paste a log here"
uv run python -m app.cli triage --file examples/hana_disk_full.log   # explicit refusal, forced in code
```

A native tool-calling loop (`search_runbook`, `lookup_tcode`; `MAX_STEPS=5`, read-only,
allow-listed) gathers evidence, then a no-tools formatter call produces a structured result with a
capped repair loop and a deterministic fallback on exhaustion. Before the result is returned:
every citation is checked against evidence actually retrieved that request (a fabricated one is
dropped), every T-code is checked against the allow-list (an unverified one is flagged, not
silently trusted), and if retrieval found nothing at all the category is forced to `out_of_scope`
in code — never left for the model to decide. `--show-trace` prints every tool call made, to
stderr, for diagnosing a surprising answer.

## Evaluate

```bash
uv run python -m eval.run_all
```

Single command, zero arguments by design (the experiment matrix lives in code, so a committed
number always corresponds to a committed matrix). Runs, in order:

- **E1** — naive fixed-800/150 chunking vs section-aligned chunking, pre-gate, winner chosen from
  the **dev split only**
- **E2** — bm25 vs dense vs hybrid on E1's winner, pre-gate, against two named baselines
- **E3** — a `MIN_SCORE` sweep on the **dev split only** (mechanically refuses to touch the test
  set — `sweep_min_score("test")` raises)
- the **headline** test-set result at the chosen floor, post-gate
- **E4** — the full triage agent vs two named baselines (`E-NoRAG`: no retrieval at all;
  `E-ClassicRAG`: one non-agentic search, no loop), end-to-end, all through the identical
  verification pipeline
- `eval/results/failures.jsonl` — every wrong/fallback/unverified case, retrieval- and
  agent-level, each with a failure type

Every number is written to `eval/results/*.json` next to the exact config that produced it
(`corpus_sha`, `git_commit`, mode, chunk strategy/`k`/`min_score` for retrieval, `max_steps`/
`repair_attempts`/`chat_model` for the agent). Run it twice — both the retrieval and the agent's
verification-level outcomes are byte-identical, the agent via a content-addressed chat-completion
cache (`data/chat_cache/`, git-ignored) mirroring the embedding cache.

## Results (test split, post-gate, headline configuration)

Full tables with deltas against baselines, the dev sweep, per-difficulty slices, the verdict, and
Limitations: **[`eval/results/results.md`](eval/results/results.md)**. Headline numbers as last
measured:

| metric | value |
|---|---|
| mode / chunking / min_score | `hybrid` / `fixed` / `0.60` (all three measured, not guessed — see results.md) |
| recall@3 (post-gate) | 0.808 |
| MRR (post-gate) | 0.788 |
| out-of-scope gate accuracy | 1.000 |
| false refusal rate | 0.154 |

Pre-gate, hybrid beats both named baselines on the test split (0.962 recall@3 vs R-BM25's 0.846
and R-Dense-naive's 0.942). The 0.60 relevance floor — chosen from the dev sweep, not guessed — is
what correctly refuses out-of-scope queries (verified against a HANA log-volume alert that an
earlier, unvalidated 0.40 default let through); it costs a 0.154 false-refusal rate on in-scope
hard cases with no exact error code, reported rather than hidden.

### End-to-end (Feature 2, test split, n=30)

| config | category_accuracy | tcode_recall | unverified_claim_rate | valid_output_rate |
|---|---|---|---|---|
| E-NoRAG (no retrieval) | 0.600 | 0.154 | 0.767 | 0.933 |
| E-ClassicRAG (one search, no loop) | 0.700 | 0.442 | 0.767 | 1.000 |
| **agent** (full bounded loop) | 0.567 | 0.365 | 0.467 | 0.967 |

**Stated plainly, not reframed**: the full agent does **not** beat either named baseline on
category accuracy or T-code recall — `E-ClassicRAG`, a single non-agentic search, scores higher on
both. The agent does win on `unverified_claim_rate` (0.467 vs 0.767 for both baselines): it is
measurably more cautious about what it asserts, even though it is less often right overall. This is
a genuine finding about this small course-gateway model's tool-use reliability, not a defect in the
verification layer — see `eval/results/results.md` § Limitations.

## Search latency (SC-013)

Measured on the author's machine, `--mode hybrid` (one query-embedding round trip to the gateway,
dominating the cost): **typically 1.4–1.5 s**, comfortably under the 3 s interactive target. One
outlier of 7.2 s was observed during a slow gateway response — reported here rather than
smoothed over, since it is a real, if infrequent, latency tail the gateway can produce.
`--mode bm25` has no network call and is dominated by Python/`uv` startup (~2.1 s cold), not by
search itself.

## Limitations

- All eval-case logs are **synthetic**, written to resemble real SAP Basis error formats.
- The corpus covers 16 runbooks across 8 incident categories only; anything outside that scope has
  no chance of a correct answer regardless of retrieval quality.
- Single-author bias in both the runbooks and the eval-case labels.
- The BM25 tokenizer (`[A-Za-z0-9_/]+`) cannot segment Thai text — Thai queries are carried
  entirely by the dense/embedding side.
- The agent's `sources` citations are frequently empty even when the trace shows it used the
  retrieved evidence — a model-citation-discipline gap on `gemma-4-E4B-it`, not a verification bug
  (a *fabricated* citation is reliably caught and dropped; an *omitted* one is not currently
  flagged as a separate failure mode).
- A log describing two simultaneous problems gets one category — the schema has no multi-label
  support; handled without crashing, reported as a known finding (spec SC-010), not hidden.

Full detail: [`eval/results/results.md`](eval/results/results.md) § Limitations.

## Project layout

```
app/            config, llm (chat + embed, the only gateway caller), normalize, cli,
                retrieval/ (Feature 1), agent/ (Feature 2: tools, loop, formatter, verify, fallback),
                triage_service.py (Feature 2 service entry point)
data/           runbooks/, tcodes.json, index/ (generated, committed), cache/ + chat_cache/ (generated, ignored)
eval/           cases_dev.jsonl, cases_test.jsonl, schema, metrics, run_retrieval, run_e2e, run_all, results/
examples/       sample logs for the commands above (never runbook text)
tests/          offline, gateway mocked — uv run pytest
specs/001-runbook-retrieval-eval/   Feature 1: spec, plan, research, data model, contracts, tasks
specs/002-triage-agent/             Feature 2: spec, plan, research, data model, contracts, tasks
```

## Out of scope (both features)

Any HTTP API or web UI (Feature 3, not started), multi-turn conversation, connecting to a live SAP
system, and executing any fix.
