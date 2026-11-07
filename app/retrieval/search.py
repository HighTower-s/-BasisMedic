"""SERVICE: search(query, mode, k, min_score) -> list[Hit] — the single retrieval entry
point shared by the CLI and the eval harness (Constitution VI, contracts/search.md)."""

from app import config
from app.normalize import cap_length, extract_key_tokens, strip_noise
from app.retrieval.store import Store
from app.schemas import Hit, RetrievalMode

MIN_QUERY_CHARS = 10
MAX_QUERY_CHARS = 4000


class InvalidQueryError(Exception):
    """Query is empty, whitespace-only, or outside the accepted length range (FR-019)."""


def _validate(query: str) -> str:
    stripped = query.strip()
    if not stripped or len(stripped) < MIN_QUERY_CHARS or len(stripped) > MAX_QUERY_CHARS:
        raise InvalidQueryError(
            f"query must be {MIN_QUERY_CHARS}-{MAX_QUERY_CHARS} non-whitespace characters, "
            f"got {len(stripped)}"
        )
    return stripped


def _normalize_query(raw: str) -> str:
    text = strip_noise(raw)
    text, _truncated = cap_length(text, limit=2000)
    tokens = extract_key_tokens(raw)
    if tokens:
        text = text + "\n" + " ".join(tokens)
    return text


def _collapse_to_best_per_doc(scored: list[tuple]) -> list[tuple]:
    """Best-scoring chunk per doc_id (FR-015, R-07); stable tie-break on chunk_id."""
    best: dict[str, tuple] = {}
    for chunk, score in scored:
        current = best.get(chunk.doc_id)
        if current is None or score > current[1]:
            best[chunk.doc_id] = (chunk, score)
    return sorted(best.values(), key=lambda pair: (-pair[1], pair[0].chunk_id))


def fuse_rrf(dense_ranked: list[str], bm25_ranked: list[str], k: int = 60) -> dict[str, float]:
    """RRF over ranks, never raw scores, so the two incomparable scales never mix.
    Correct when either input is empty (Thai queries yield zero BM25 tokens, R-05)."""
    scores: dict[str, float] = {}
    for i, doc_id in enumerate(dense_ranked, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + i)
    for i, doc_id in enumerate(bm25_ranked, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + i)
    return scores


def _rank_bm25_collapsed(normalized: str, store: Store) -> list[tuple]:
    scored = [(c, s) for c, s in store.bm25_search(normalized) if s > 0]
    return _collapse_to_best_per_doc(scored)


def _rank_dense_collapsed(normalized: str, store: Store) -> list[tuple]:
    from app import llm  # the ONLY gateway caller (Constitution VI); never imported in bm25 mode
    import numpy as np

    vector = np.asarray(llm.embed([normalized])[0], dtype=np.float32)
    scored = store.cosine_search(vector)
    return _collapse_to_best_per_doc(scored)


def rank(query: str, *, mode: RetrievalMode | None = None, store: Store | None = None) -> list[Hit]:
    """Full ranked, collapsed candidate list — no gate, no k-truncation. Used directly by
    the eval harness for pre-gate metrics (R-01); search() gates and truncates this."""
    mode = mode or config.retrieval_mode()
    stripped = _validate(query)
    store = store or Store.load()
    normalized = _normalize_query(stripped)

    if mode == "bm25":
        collapsed = _rank_bm25_collapsed(normalized, store)
        return [
            Hit(chunk_id=c.chunk_id, doc_id=c.doc_id, section=c.section, text=c.text,
                bm25_score=score, rank=i + 1)
            for i, (c, score) in enumerate(collapsed)
        ]

    if mode == "dense":
        collapsed = _rank_dense_collapsed(normalized, store)
        return [
            Hit(chunk_id=c.chunk_id, doc_id=c.doc_id, section=c.section, text=c.text,
                dense_score=score, rank=i + 1)
            for i, (c, score) in enumerate(collapsed)
        ]

    if mode == "hybrid":
        dense_collapsed = _rank_dense_collapsed(normalized, store)
        bm25_collapsed = _rank_bm25_collapsed(normalized, store)
        dense_scores = {c.doc_id: s for c, s in dense_collapsed}
        bm25_scores = {c.doc_id: s for c, s in bm25_collapsed}
        fused = fuse_rrf(
            [c.doc_id for c, _ in dense_collapsed],
            [c.doc_id for c, _ in bm25_collapsed],
        )
        chunk_by_doc = {c.doc_id: c for c, _ in dense_collapsed}
        for c, _ in bm25_collapsed:
            chunk_by_doc.setdefault(c.doc_id, c)
        ordered = sorted(
            fused.items(), key=lambda pair: (-pair[1], chunk_by_doc[pair[0]].chunk_id)
        )
        return [
            Hit(
                chunk_id=chunk_by_doc[doc_id].chunk_id,
                doc_id=doc_id,
                section=chunk_by_doc[doc_id].section,
                text=chunk_by_doc[doc_id].text,
                dense_score=dense_scores.get(doc_id),
                bm25_score=bm25_scores.get(doc_id),
                fused_score=fused_score,
                rank=i + 1,
            )
            for i, (doc_id, fused_score) in enumerate(ordered)
        ]

    raise ValueError(f"unknown retrieval mode {mode!r}")


def search(
    query: str,
    *,
    mode: RetrievalMode | None = None,
    k: int | None = None,
    min_score: float | None = None,
    store: Store | None = None,
) -> list[Hit]:
    mode = mode or config.retrieval_mode()
    k = k if k is not None else config.top_k()
    min_score = min_score if min_score is not None else config.min_score()
    stripped = _validate(query)
    store = store or Store.load()

    ranked = rank(query, mode=mode, store=store)
    rare = store.rare_tokens(stripped)

    if mode == "bm25":
        if not rare:
            return []
    elif mode in ("dense", "hybrid"):
        # The gate always reads the dense cosine, never the RRF score (contracts/search.md).
        top1_cosine = ranked[0].dense_score if ranked else None
        if (top1_cosine is None or top1_cosine < min_score) and not rare:
            return []
    else:
        raise ValueError(f"unknown retrieval mode {mode!r}")

    return [hit.model_copy(update={"rank": i + 1}) for i, hit in enumerate(ranked[:k])]
