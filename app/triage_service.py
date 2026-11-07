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
from app.schemas import Hit, TriageResult


def _normalize_log(raw: str) -> str:
    text = strip_noise(raw)
    text, _truncated = cap_length(text, limit=2000)
    tokens = extract_key_tokens(raw)
    if tokens:
        text = text + "\n" + " ".join(tokens)
    return text


def _gather_for_mode(
    normalized: str, *, mode: str, store: Store, trace: list[ToolCallRecord] | None
) -> list[Hit]:
    """R-08: E-NoRAG makes no retrieval call at all; E-ClassicRAG makes exactly one;
    the full agent runs the bounded loop. `trace`, if given, is appended with every
    ToolCallRecord made — purely diagnostic (CLI --show-trace), never read by this
    function's own logic."""
    if mode == "E-NoRAG":
        return []
    if mode == "E-ClassicRAG":
        text, hits = search_runbook({"query": normalized}, store=store)
        if trace is not None:
            trace.append(ToolCallRecord(tool="search_runbook", args={"query": normalized}, normalized_key="", result=text, hits=hits))
        return hits
    records = gather_evidence(normalized, store=store, max_steps=config.max_steps())
    if trace is not None:
        trace.extend(records)
    return [hit for record in records for hit in record.hits]


def triage(
    log: str, *, mode: str = "agent", store: Store | None = None,
    trace: list[ToolCallRecord] | None = None,
) -> TriageResult:
    stripped = log.strip()
    if not stripped or len(stripped) < MIN_QUERY_CHARS or len(stripped) > MAX_QUERY_CHARS:
        raise InvalidQueryError(
            f"log must be {MIN_QUERY_CHARS}-{MAX_QUERY_CHARS} non-whitespace characters, "
            f"got {len(stripped)}"
        )

    store = store or Store.load()
    normalized = _normalize_log(stripped)

    evidence = _gather_for_mode(normalized, mode=mode, store=store, trace=trace)
    result = format_result(evidence, normalized)

    result = verify_citations(result, evidence)
    result = verify_tcodes(result, store.tcodes)
    return result
