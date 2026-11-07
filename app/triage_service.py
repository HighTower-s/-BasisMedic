"""SERVICE: triage(log) -> TriageResult. The single triage entry point shared by the
CLI and the eval harness (Constitution VI, specs/002-triage-agent/contracts/service.md)."""

from app import config
from app.agent.formatter import format_result
from app.agent.loop import gather_evidence
from app.agent.tools import search_runbook
from app.agent.verify import verify_citations, verify_tcodes
from app.normalize import cap_length, extract_key_tokens, strip_noise
from app.retrieval.search import InvalidQueryError, MAX_QUERY_CHARS, MIN_QUERY_CHARS
from app.agent.loop import ToolCallRecord
from app.retrieval.store import Store
from app.schemas import Hit, Step, TriageResult


def _normalize_log(raw: str) -> str:
    text = strip_noise(raw)
    text, _truncated = cap_length(text, limit=2000)
    tokens = extract_key_tokens(raw)
    if tokens:
        text = text + "\n" + " ".join(tokens)
    return text


def _gather_for_mode(
    normalized: str, *, mode: str, store: Store, trace: list[ToolCallRecord] | None,
    retrieval_mode: str | None,
) -> list[Hit]:
    """R-08: E-NoRAG makes no retrieval call at all; E-ClassicRAG makes exactly one;
    the full agent runs the bounded loop. `trace`, if given, is appended with every
    ToolCallRecord made — purely diagnostic (CLI --show-trace), never read by this
    function's own logic. `retrieval_mode` is Feature 1's bm25/dense/hybrid selector,
    distinct from this function's own agent/E-NoRAG/E-ClassicRAG `mode`."""
    if mode == "E-NoRAG":
        return []
    if mode == "E-ClassicRAG":
        text, hits = search_runbook({"query": normalized}, store=store, mode=retrieval_mode)
        if trace is not None:
            trace.append(ToolCallRecord(tool="search_runbook", args={"query": normalized}, normalized_key="", result=text, hits=hits))
        return hits
    records = gather_evidence(normalized, store=store, max_steps=config.max_steps(), mode=retrieval_mode)
    if trace is not None:
        trace.extend(records)
    return [hit for record in records for hit in record.hits]


def _out_of_scope_result() -> TriageResult:
    return TriageResult(
        category="out_of_scope",
        summary="nothing in the corpus cleared the relevance floor for this log",
        tcodes=[],
        unverified_tcodes=[],
        steps=[Step(action="Not covered by the runbooks; investigate manually or escalate.", tcode=None)],
        escalate_to=None,
        sources=[],
        confidence="low",
    )


def triage(
    log: str, *, mode: str = "agent", store: Store | None = None,
    trace: list[ToolCallRecord] | None = None, retrieval_mode: str | None = None,
) -> TriageResult:
    stripped = log.strip()
    if not stripped or len(stripped) < MIN_QUERY_CHARS or len(stripped) > MAX_QUERY_CHARS:
        raise InvalidQueryError(
            f"log must be {MIN_QUERY_CHARS}-{MAX_QUERY_CHARS} non-whitespace characters, "
            f"got {len(stripped)}"
        )

    store = store or Store.load()
    normalized = _normalize_log(stripped)

    evidence = _gather_for_mode(
        normalized, mode=mode, store=store, trace=trace, retrieval_mode=retrieval_mode
    )

    # R-07: when retrieval was actually attempted (agent/E-ClassicRAG) and found nothing,
    # force out_of_scope in code before spending a model call on a draft that would be
    # discarded. E-NoRAG deliberately skips this -- it never attempts retrieval at all,
    # so empty evidence there is not evidence of an out-of-scope incident.
    if mode in ("agent", "E-ClassicRAG") and not evidence:
        result = _out_of_scope_result()
    else:
        result = format_result(evidence, normalized)

    result = verify_citations(result, evidence)
    result = verify_tcodes(result, store.tcodes)
    return result
