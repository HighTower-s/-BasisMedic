"""Read-only, allow-listed agent tools (Constitution IV). Neither tool modifies the
corpus, the index, or any external system. See specs/002-triage-agent/contracts/tools.md."""

import re

from app.retrieval.runbooks import load_tcodes
from app.retrieval.search import InvalidQueryError, MAX_QUERY_CHARS, MIN_QUERY_CHARS, search
from app.retrieval.store import Store
from app.schemas import Hit, TCODE_RE


def search_runbook(
    args: dict, *, store: Store, mode: str | None = None, k: int | None = None,
    min_score: float | None = None,
) -> tuple[str, list[Hit]]:
    """Returns (text shown to the model, Hits actually retrieved — for Evidence)."""
    query = str(args.get("query") or "").strip()
    if not (MIN_QUERY_CHARS <= len(query) <= MAX_QUERY_CHARS):
        return (
            f"error: query must be {MIN_QUERY_CHARS}-{MAX_QUERY_CHARS} characters, got {len(query)}",
            [],
        )
    try:
        hits = search(query, mode=mode, k=k, min_score=min_score, store=store)
    except InvalidQueryError as exc:
        return f"error: {exc}", []

    if not hits:
        return "NO_RELEVANT_RUNBOOK", []

    lines = [f"[{h.rank}] ({h.chunk_id}) {h.text[:300]}" for h in hits]
    return "\n".join(lines), hits


def lookup_tcode(args: dict, *, store: Store | None = None, tcodes_path=None) -> str:
    code = str(args.get("code") or "").strip()
    if not re.fullmatch(TCODE_RE, code):
        return f"error: {code!r} does not look like a transaction code"
    tcodes = store.tcodes if store is not None else load_tcodes(tcodes_path)
    description = tcodes.get(code)
    if description is None:
        return "unknown tcode"
    return f"{code}: {description}"


TOOLS = {
    "search_runbook": search_runbook,
    "lookup_tcode": lookup_tcode,
}
