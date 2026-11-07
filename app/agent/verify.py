"""Post-check: citation verification, T-code verification, out_of_scope forcing.
Never trusts the model's own text — every claim is checked against evidence actually
retrieved during this same request (Constitution III, research.md R-06, R-07)."""

from app.schemas import Hit, TriageResult


def verify_citations(result: TriageResult, evidence: list[Hit]) -> TriageResult:
    """Drop any source not present in evidence actually returned by search_runbook
    during this request (FR-009). Never raises."""
    known_ids = {hit.chunk_id for hit in evidence}
    kept = [source for source in result.sources if source in known_ids]
    if kept == result.sources:
        return result
    return result.model_copy(update={"sources": kept})


def verify_tcodes(result: TriageResult, allow_list: dict[str, str]) -> TriageResult:
    """Partition top-level tcodes into verified (stay) and unverified (moved, never
    dropped) against the allow-list (FR-010). Also sanitises each Step.tcode the same
    way (data-model.md § 1: "must be a key of data/tcodes.json by the time verify_tcodes
    has run") — a step citing an unverified code (e.g. a program name mistaken for a
    T-code) has that field cleared to None rather than silently passed through. Never
    raises."""
    verified = [code for code in result.tcodes if code in allow_list]
    unverified = [code for code in result.tcodes if code not in allow_list]

    new_steps = []
    steps_changed = False
    for step in result.steps:
        if step.tcode is not None and step.tcode not in allow_list:
            if step.tcode not in unverified:
                unverified.append(step.tcode)
            new_steps.append(step.model_copy(update={"tcode": None}))
            steps_changed = True
        else:
            new_steps.append(step)

    if not unverified and not steps_changed:
        return result
    return result.model_copy(
        update={
            "tcodes": verified,
            "unverified_tcodes": result.unverified_tcodes + unverified,
            "steps": new_steps,
        }
    )


def force_out_of_scope(result: TriageResult) -> TriageResult:
    """Overwrite category to out_of_scope with empty tcodes/sources, regardless of what
    the model asserted (FR-011, FR-012, research.md R-07)."""
    if result.category == "out_of_scope":
        return result
    return result.model_copy(
        update={"category": "out_of_scope", "tcodes": [], "unverified_tcodes": [], "sources": []}
    )
