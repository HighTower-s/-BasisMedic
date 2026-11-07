"""Phase 2: no-tools formatter call, JSON extraction, Pydantic validation, a capped
repair loop, falling back to a deterministic result on exhaustion (research.md R-01, R-04,
R-05). Never raises on malformed model output — always returns a valid TriageResult."""

import json
import re

from pydantic import ValidationError

from app import llm
from app.agent.fallback import build_fallback
from app.schemas import Hit, Step, TriageResult

REPAIR_ATTEMPTS = 2  # code constant, not an env var (research.md R-04)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)

_FORMATTER_SYSTEM_PROMPT = (
    "Convert the diagnosis into JSON. Reply with ONLY a JSON object, no markdown, no explanation."
)

_SCHEMA_HINT = (
    '{"category": "<one of memory_dump|timeout|job_failure|lock_issue|update_error|'
    'transport_error|user_auth|rfc_error|out_of_scope>", "summary": "<=300 chars", '
    '"tcodes": ["..."], "steps": [{"action": "...", "tcode": "..."}], '
    '"escalate_to": "basis|developer|security|dba|network|sap_support|null", '
    '"sources": ["doc_id#section", "..."], "confidence": "high|medium|low"}'
)


def _extract_json_text(text: str) -> str:
    fence_match = _FENCE_RE.search(text)
    candidate = fence_match.group(1) if fence_match else text
    start = candidate.find("{")
    if start == -1:
        return candidate
    depth = 0
    for i in range(start, len(candidate)):
        if candidate[i] == "{":
            depth += 1
        elif candidate[i] == "}":
            depth -= 1
            if depth == 0:
                return candidate[start : i + 1]
    return candidate[start:]


def _evidence_text(evidence: list[Hit]) -> str:
    if not evidence:
        return "(no retrieval was performed; answer directly from the log, but only name T-codes you are sure of)"
    return "\n".join(f"[{i + 1}] ({hit.chunk_id}) {hit.text[:500]}" for i, hit in enumerate(evidence))


def _build_messages(evidence: list[Hit], log: str) -> list[dict]:
    user_content = (
        f"EVIDENCE:\n{_evidence_text(evidence)}\n\n"
        f"LOG:\n<log>\n{log}\n</log>\n\n"
        f"Reply with ONLY a JSON object matching this schema: {_SCHEMA_HINT}\n"
        "Use only T-codes and sources that appear in EVIDENCE."
    )
    return [
        {"role": "system", "content": _FORMATTER_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _empty_evidence_fallback() -> TriageResult:
    """build_fallback requires at least one Hit; this covers the E-NoRAG edge case
    where repair is exhausted with zero evidence to fall back to."""
    return TriageResult(
        category="out_of_scope",
        summary="formatting failed and no evidence was available to fall back to",
        tcodes=[],
        unverified_tcodes=[],
        steps=[Step(action="Automatic formatting failed; investigate this log manually.", tcode=None)],
        escalate_to=None,
        sources=[],
        confidence="low",
    )


def format_result(evidence: list[Hit], log: str) -> TriageResult:
    messages = _build_messages(evidence, log)

    for _attempt in range(REPAIR_ATTEMPTS + 1):
        response = llm.chat(messages, tools=None, temperature=0)
        content = response["choices"][0]["message"].get("content") or ""
        json_text = _extract_json_text(content)
        try:
            data = json.loads(json_text)
            return TriageResult.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {"role": "user", "content": f"That was invalid: {exc}. Reply again with ONLY corrected JSON."}
            )

    return build_fallback(evidence) if evidence else _empty_evidence_fallback()
