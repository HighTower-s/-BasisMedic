import pytest
from pydantic import ValidationError

from app.schemas import Step, TriageResult


def _result(**overrides) -> dict:
    base = dict(
        category="memory_dump",
        summary="short summary",
        tcodes=["ST22"],
        steps=[Step(action="Open ST22 and read the dump.", tcode="ST22")],
        escalate_to="developer",
        sources=["mem_tsv_tnew_page_alloc#check"],
        confidence="high",
    )
    base.update(overrides)
    return base


def test_out_of_scope_with_tcodes_is_rejected():
    with pytest.raises(ValidationError):
        TriageResult(**_result(category="out_of_scope", tcodes=["ST22"], sources=[]))


def test_out_of_scope_with_sources_is_rejected():
    with pytest.raises(ValidationError):
        TriageResult(**_result(category="out_of_scope", tcodes=[], sources=["x#y"]))


def test_out_of_scope_with_no_tcodes_or_sources_is_valid():
    result = TriageResult(**_result(category="out_of_scope", tcodes=[], sources=[]))
    assert result.category == "out_of_scope"


def test_step_action_too_short_is_rejected():
    with pytest.raises(ValidationError):
        Step(action="hi", tcode=None)


def test_tcodes_over_six_is_rejected():
    with pytest.raises(ValidationError):
        TriageResult(**_result(tcodes=["ST22"] * 7))


def test_steps_over_eight_is_rejected():
    step = Step(action="Open ST22 and read the dump.", tcode="ST22")
    with pytest.raises(ValidationError):
        TriageResult(**_result(steps=[step] * 9))


def test_steps_requires_at_least_one():
    with pytest.raises(ValidationError):
        TriageResult(**_result(steps=[]))


def test_summary_over_300_chars_is_rejected():
    with pytest.raises(ValidationError):
        TriageResult(**_result(summary="x" * 301))


def test_normal_result_round_trips():
    result = TriageResult(**_result())
    assert result.confidence == "high"
    assert result.unverified_tcodes == []
