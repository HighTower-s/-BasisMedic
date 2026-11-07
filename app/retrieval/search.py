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


def rank(query: str, *, mode: RetrievalMode | None = None, store: Store | None = None) -> list[Hit]:
    """Full ranked, collapsed candidate list — no gate, no k-truncation. Used directly by
    the eval harness for pre-gate metrics (R-01); search() gates and truncates this."""
    mode = mode or config.retrieval_mode()
    stripped = _validate(query)
    store = store or Store.load()
    normalized = _normalize_query(stripped)

    if mode == "bm25":
        scored = [(c, s) for c, s in store.bm25_search(normalized) if s > 0]
        collapsed = _collapse_to_best_per_doc(scored)
        return [
            Hit(chunk_id=c.chunk_id, doc_id=c.doc_id, section=c.section, text=c.text,
                bm25_score=score, rank=i + 1)
            for i, (c, score) in enumerate(collapsed)
        ]

    if mode in ("dense", "hybrid"):
        raise NotImplementedError(f"mode={mode!r} is implemented in Phase 5 (US3)")

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
        raise NotImplementedError(f"mode={mode!r} is implemented in Phase 5 (US3)")
    else:
        raise ValueError(f"unknown retrieval mode {mode!r}")

    return [hit.model_copy(update={"rank": i + 1}) for i, hit in enumerate(ranked[:k])]
