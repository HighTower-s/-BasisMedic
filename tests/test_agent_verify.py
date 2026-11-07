from app.agent.verify import verify_citations, verify_tcodes
from app.schemas import Hit, Step, TriageResult


def _evidence() -> list[Hit]:
    return [
        Hit(chunk_id="mem_tsv_tnew_page_alloc#check", doc_id="mem_tsv_tnew_page_alloc",
            section="Check", text="...", rank=1),
    ]


def _result(**overrides) -> TriageResult:
    base = dict(
        category="memory_dump",
        summary="a short summary",
        tcodes=["ST22"],
        steps=[Step(action="Open ST22 and read the dump.", tcode="ST22")],
        escalate_to="developer",
        sources=["mem_tsv_tnew_page_alloc#check"],
        confidence="high",
    )
    base.update(overrides)
    return TriageResult(**base)


def test_verify_citations_keeps_a_citation_present_in_evidence():
    result = _result()
    verified = verify_citations(result, _evidence())
    assert verified.sources == ["mem_tsv_tnew_page_alloc#check"]


def test_verify_citations_drops_a_fabricated_citation():
    result = _result(sources=["mem_tsv_tnew_page_alloc#check", "never_retrieved#fake"])
    verified = verify_citations(result, _evidence())
    assert verified.sources == ["mem_tsv_tnew_page_alloc#check"]


def test_verify_tcodes_keeps_an_allow_listed_code():
    result = _result()
    verified = verify_tcodes(result, {"ST22": "ABAP Dump Analysis"})
    assert verified.tcodes == ["ST22"]
    assert verified.unverified_tcodes == []


def test_verify_tcodes_moves_unknown_code_to_unverified_not_dropped():
    result = _result(tcodes=["ST22", "ZZ99"])
    verified = verify_tcodes(result, {"ST22": "ABAP Dump Analysis"})
    assert verified.tcodes == ["ST22"]
    assert verified.unverified_tcodes == ["ZZ99"]


def test_verify_tcodes_also_sanitises_step_level_tcode():
    result = _result(
        tcodes=["ST22"],
        steps=[Step(action="Investigate the report.", tcode="ZFI_MONTHLY_REPORT")],
    )
    verified = verify_tcodes(result, {"ST22": "ABAP Dump Analysis"})
    assert verified.steps[0].tcode is None
    assert "ZFI_MONTHLY_REPORT" in verified.unverified_tcodes
