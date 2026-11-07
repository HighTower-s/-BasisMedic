# Contract: `search()` service (`app/retrieval/search.py`)

**Feature**: `001-runbook-retrieval-eval` | **Layer**: service

The single retrieval entry point. The CLI and the eval harness call this exact function with the same
arguments, so the measured system and the demonstrated system cannot diverge (Constitution VI).

```python
def search(
    query: str,
    *,
    mode: RetrievalMode = ...,       # from config
    k: int = ...,                    # from config, default 3
    min_score: float = ...,          # from config
    store: Store | None = None,      # injected for tests; loaded from data/index/ otherwise
) -> list[Hit]:
    ...
```

Returns a list of 0 to `k` `Hit`s. An empty list is a *successful* refusal, not an error (FR-018).

---

## Pipeline

```
query
  ├─ 1. validate            InvalidQueryError if stripped length < 10, > 4000, or
  │                         whitespace-only                                                (FR-019)
  ├─ 2. normalize           strip timestamps/addresses, cap the query at 2000 chars,
  │                         extract key tokens, append them to the query text              (R-10)
  ├─ 3. retrieve            mode-specific ranked candidate list over all chunks
  ├─ 4. collapse            best-scoring chunk per doc_id, for every caller                (FR-015, R-07)
  ├─ 5. gate                mode-specific floor; may return []                             (FR-018, R-02)
  └─ 6. truncate + rank     take k, assign rank 1..n
```

Step 4 precedes step 5: the gate decides on the best evidence available, and `k` applies to distinct
documents so "3 results" always means three candidate answers.

---

## Retrieval modes

| Mode | Ranking | Network | Score on `Hit` |
|---|---|---|---|
| `bm25` | `BM25Okapi` over `[A-Za-z0-9_/]+` lower-cased tokens | **none** (FR-017, SC-012) | `bm25_score` |
| `dense` | cosine of the query vector against the normalised chunk matrix (dot product) | one embed call | `dense_score` |
| `hybrid` | RRF over the two ranked lists: `score = Σ 1/(60 + rank)` | one embed call | `fused_score` (+ both components) |

**Hybrid details**: fusion is over *ranks*, never raw scores, so the two incomparable scales never
mix. `fuse_rrf` must be correct when either input list is empty — the normal case for Thai queries,
which yield zero BM25 tokens (R-05). In `hybrid` mode the `Hit` carries `dense_score` and
`bm25_score` alongside `fused_score`, because the dense component is what the gate reads.

---

## Gate semantics (FR-018, R-02, R-03)

```
rare = rare_tokens(query)                  # corpus-vocabulary ∩ (error-code regex ∪ tcode allow-list)

mode in {dense, hybrid}:
    return [] if (dense_top1_cosine < min_score) and (rare == ∅)
mode == bm25:
    return [] if rare == ∅
```

- The dense cosine is the only absolute-scaled signal available; RRF scores are unbounded and
  corpus-dependent, so they cannot carry a meaningful floor.
- `bm25` mode has no cosine at all, which is why its gate is the token rule alone. Results tables
  label that row's gate as weaker rather than presenting it as like-for-like (Constitution II).
- A rare token rescues a low-cosine query: an exact `TSV_TNEW_PAGE_ALLOC_FAILED` in an oddly
  formatted log must not be refused just because embedding similarity is diluted by surrounding noise.
- **This rule is a hypothesis.** Experiment E3 tests whether it separates in-scope from out-of-scope
  on the dev set. If it does not, it is replaced and the replacement reported with the evidence.

---

## Guarantees

1. **Resolvable citations.** Every `Hit.chunk_id` resolves to existing corpus text; zero dangling
   addresses across both splits (FR-010, SC-005).
2. **Distinct documents.** No two `Hit`s in one result list share a `doc_id` (FR-015).
3. **Ordering.** Strictly descending by the active mode's ranking score; `rank` is 1-based and
   contiguous.
4. **Bounded size.** `0 <= len(result) <= k`.
5. **Monotonic floor.** For a fixed query and mode, raising `min_score` never increases the number of
   results (FR-018, acceptance scenario US3-3).
6. **Determinism.** Identical `(query, mode, k, min_score, corpus_sha)` yields an identical list —
   the basis of FR-036 and SC-004. Guaranteed by cached embeddings and by stable tie-breaking on
   `chunk_id` when scores are equal.
7. **Index freshness.** Raises `StaleIndexError` when the loaded manifest's `corpus_sha` disagrees
   with the current corpus, rather than returning text that no longer exists (FR-020).
8. **No model reasoning.** No chat model is reachable from this path. A refusal is a code decision
   (Constitution III).

---

## Errors

| Exception | Raised when | CLI exit |
|---|---|---|
| `InvalidQueryError` | empty, whitespace-only, or `< 10` characters after stripping | 2 |
| `StaleIndexError` | manifest `corpus_sha` ≠ current corpus hash, no index present, or `dense`/`hybrid` requested against a `--no-embed` index (`n_vectors == 0`) | 5 |
| `UpstreamError` | gateway error/timeout while embedding the query (`dense`/`hybrid` only) | 4 |
| `ConfigError` | required env var missing or malformed | 3 |

Exceptions are raised, never swallowed into an empty result — an empty list must mean "nothing
relevant", never "something broke" (Constitution II).

---

## Repository and single-gateway seams

```
search()                      service   ← CLI and eval both call only this
  ├── store.Store             repository: chunks + normalised matrix + manifest; cosine and BM25
  ├── bm25.rare_tokens()      repository-adjacent: corpus vocabulary ∩ allow-list/regex
  ├── normalize.*             pure functions, no I/O
  └── llm.embed()             the ONLY gateway caller in the project (Constitution VI)
```

`Store` is injectable so every test runs offline against a small fake corpus with `embed` mocked.

---

## Test obligations

Offline, with `app.llm.embed` mocked (Constitution VIII):

| Test | Asserts |
|---|---|
| `test_gate.py` | all four gate branches; `bm25` mode never consults a cosine; monotonicity in `min_score` |
| `test_fusion.py` | RRF arithmetic against hand-computed ranks; empty-dense and empty-BM25 inputs |
| `test_bm25.py` | `TSV_TNEW_PAGE_ALLOC_FAILED`, `SM37`, `RC=8` tokenisation; Thai input yields zero tokens (R-05); `rare_tokens` boundaries |
| `test_store.py` | chunk-line ↔ matrix-row alignment; `StaleIndexError` on corpus-hash mismatch |
| `test_chunk.py` | `fixed(800,150)` window boundaries; `by_section` yields 6 chunks with the context prefix |
| `test_normalize.py` | timestamp/address stripping, 2000-char query cap, key-token extraction |
| (search-level) | de-duplication to distinct `doc_id`s; `rank` contiguity; `k` bound; stable tie-break |
