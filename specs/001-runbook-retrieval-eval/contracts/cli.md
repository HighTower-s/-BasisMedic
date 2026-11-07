# Contract: CLI (`app/cli.py`)

**Feature**: `001-runbook-retrieval-eval` | **Layer**: edge

The only interactive surface in this feature, and the live-demo fallback Constitution VI requires to
always work. `app/cli.py` parses arguments, calls one service function, formats output, and maps
exceptions to exit codes. It contains no retrieval, scoring, or validation logic of its own.

See [plan.md § Structure Decision](../plan.md#structure-decision) for why the CLI lives here rather
than in `app/retrieval/search.py`.

---

## `python -m app.cli ingest`

Builds the search index from the corpus (FR-008).

```
uv run python -m app.cli ingest [--strategy {section,fixed}] [--no-embed] [--quiet]
```

| Argument | Default | Meaning |
|---|---|---|
| `--strategy` | `$CHUNK_STRATEGY` (`section`) | chunking strategy to build with |
| `--no-embed` | off | build chunks and BM25 structures only; **no gateway calls** |
| `--quiet` | off | suppress the per-runbook lines, keep the summary |

**Behaviour**: load and validate the corpus → chunk → embed (cache-first, unless `--no-embed`) →
write `chunks.jsonl`, `embeddings.npy`, `manifest.json` into `data/index.tmp/` → atomically replace
`data/index/` (R-04).

**`--no-embed` exists for SC-012 and R-12 step 6**: it produces an index sufficient for `--mode bm25`
with no API key and no network, so the first real recall@3 can be measured before any embedding code
is trusted. The manifest records `embed_model: null`, `embed_dim: null`, `n_vectors: 0`, and
`embeddings.npy` is absent. Requesting `--mode dense` or `--mode hybrid` against such an index fails
with exit 5 and a message naming the fix (re-ingest without `--no-embed`) — never a silent fallback
to keyword-only, which would misreport which mode produced a number.

**Required output on success** (FR-012 — an incomplete build must be visible, not silent):

```
corpus      : 16 runbooks, 8 categories, 96 sections
tcodes      : 41 allow-listed
strategy    : section
embeddings  : 96 vectors, dim 1024  (cache: 96 hit, 0 miss)
index       : data/index/  corpus_sha=3f9a1c2e…  commit=37eb1df
```

The cache hit/miss line is load-bearing: `0 miss` on a rebuild is how the author confirms the
determinism claim behind SC-004 without reading code. Under `--no-embed` that line reads
`embeddings  : skipped (--no-embed); bm25 only`.

**Exit codes**

| Code | Condition |
|---|---|
| 0 | index written |
| 2 | corpus invalid — `CorpusError`, naming file and offending value (FR-007) |
| 3 | config missing/invalid — e.g. no `OPENAI_API_KEY` for a strategy needing embeddings |
| 4 | gateway failure — `UpstreamError`; **previous index left intact** (R-04) |

---

## `python -m app.cli search`

Searches the corpus with a log or free-text query (FR-013).

```
uv run python -m app.cli search "<query text>"
uv run python -m app.cli search --file path/to/sample.log
      [--mode {dense,bm25,hybrid}] [--k 3] [--min-score 0.40] [--json] [--show-tokens]
```

| Argument | Default | Meaning |
|---|---|---|
| positional / `--file` | — | exactly one required; `--file` reads UTF-8 |
| `--mode` | `$RETRIEVAL_MODE` (`hybrid`) | retrieval mode |
| `--k` | `$TOP_K` (`3`) | maximum results |
| `--min-score` | `$MIN_SCORE` | relevance floor (FR-018) |
| `--json` | off | emit the `Hit` list as JSON for scripting |
| `--show-tokens` | off | print the key tokens `normalize` extracted and the rare tokens the gate saw |

**Human output** — one block per hit, best first, each showing the resolvable address and the score
actually ranked by (FR-014):

```
1. mem_tsv_tnew_page_alloc#symptoms   cosine 0.731   (memory_dump)
   Dump "No more storage space available for extending an internal table"; job fails mid-run; …

2. mem_tsv_tnew_page_alloc#check      cosine 0.688   (memory_dump)
   ST22 → Error analysis for requested vs used size; ST02 for EM/heap; RZ11 for ztta/roll_extension; …
```

**Nothing-relevant output** — the explicit refusal FR-018 requires. Zero results, non-empty message,
exit 0 (a correct refusal is a success):

```
NO_RELEVANT_RUNBOOK
Nothing in the corpus cleared the relevance floor (min_score=0.40).
  best dense score : 0.291
  rare tokens seen : none
This incident is not covered by the runbooks.
```

`--show-tokens` additionally prints the extracted key tokens, which is how a surprising refusal gets
diagnosed during a demo.

**Exit codes**

| Code | Condition |
|---|---|
| 0 | results returned **or** a clean no-relevant-runbook refusal |
| 2 | invalid query — `InvalidQueryError`: empty, whitespace-only, or `< 10` characters (FR-019, R-10) |
| 3 | config missing/invalid |
| 4 | gateway failure (`dense`/`hybrid` only — `bm25` never calls out, FR-017) |
| 5 | no index, or index stale against the corpus — `StaleIndexError`, message names `python -m app.cli ingest` (FR-020) |

---

## Cross-cutting rules

1. **No business logic.** Every command body is: parse args → call one service function → format →
   map exception to exit code. Anything else belongs in `app/retrieval/`.
2. **Nothing imports the CLI.** `app/retrieval/*` and `eval/*` must never import `app.cli`; a test
   asserts this (Constitution VI — the core and the eval never depend on an edge).
3. **Errors to stderr, results to stdout**, so `--json` output stays pipeable.
4. **No secrets in output.** Config echoing prints the base URL and model names, never the API key.
5. **`bm25` mode is fully offline.** No code path in `--mode bm25` touches `app.llm` (FR-017,
   SC-012). A test asserts the gateway client is never constructed in that mode.
6. **Two length limits, both announced.** Input outside 10–4000 characters is rejected (exit 2);
   accepted input is normalised down to a ≤ 2000-character query, and that truncation is noted on
   stderr (R-10, `docs/prepare/04_system_flow.md` § B2).

---

## Evaluation entry points

Not part of `app/cli.py`, but the other two commands a user runs. Both are module entry points so the
eval harness never depends on the CLI edge.

```
uv run python -m eval.run_retrieval --split {dev,test} --mode … --strategy … --min-score … --name …
uv run python -m eval.run_all
```

`run_all` is the single command FR-031 and SC-004 refer to: it executes E1 → E2 → E3 in order and
writes `eval/results/*.json`, `failures.jsonl`, and `results.md`. It accepts no tuning arguments —
the experiment matrix is in code, so the committed numbers always correspond to a committed matrix.

**The dev-only guard** (FR-041): `sweep_min_score(split)` raises `ValueError` for any split other
than `"dev"`, proven by `tests/test_sweep_guard.py`. The test set is read by reporting runs only.
