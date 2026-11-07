"""Deterministic downgrade when the formatter's repair loop is exhausted. No model call;
built directly from the single best-retrieved runbook's own already-validated front-matter,
so it cannot itself fail validation (research.md R-05)."""

import re
from pathlib import Path

from app import config
from app.retrieval.runbooks import load_tcodes, parse_runbook
from app.schemas import Hit, Step, TriageResult

_NUMBERED_LINE_RE = re.compile(r"^\s*\d+\.\s*(.+)$")
_LEADING_TCODE_RE = re.compile(r"^([A-Z][A-Z0-9_/]{1,19})\b")


def _steps_from_check_section(check_text: str) -> list[Step]:
    steps = []
    for line in check_text.splitlines():
        match = _NUMBERED_LINE_RE.match(line)
        if not match:
            continue
        body = match.group(1).strip()
        if len(body) < 5:
            continue
        tcode_match = _LEADING_TCODE_RE.match(body)
        tcode = tcode_match.group(1) if tcode_match else None
        steps.append(Step(action=body, tcode=tcode))
    if not steps:
        steps = [Step(action="Review the runbook's Check section manually.", tcode=None)]
    return steps


def build_fallback(
    evidence: list[Hit], *, runbook_dir: Path | None = None, tcodes_path: Path | None = None
) -> TriageResult:
    if not evidence:
        raise ValueError("build_fallback requires at least one piece of evidence")

    best = min(evidence, key=lambda hit: hit.rank)
    runbook_dir = runbook_dir or config.RUNBOOK_DIR
    tcodes = load_tcodes(tcodes_path)
    path = runbook_dir / f"{best.doc_id}.md"
    runbook = parse_runbook(path, tcodes)

    return TriageResult(
        category=runbook.category,
        summary=f"Best match from the corpus (repair exhausted): {runbook.title}",
        tcodes=list(runbook.tcodes),
        steps=_steps_from_check_section(runbook.sections["Check"]),
        escalate_to=runbook.escalate_to,
        sources=[best.chunk_id],
        confidence="low",
    )
