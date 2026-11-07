from app.agent.fallback import build_fallback
from app.schemas import Hit


def test_fallback_builds_a_valid_result_from_the_best_evidence(fake_corpus):
    runbook_dir, tcodes_path = fake_corpus
    hit = Hit(
        chunk_id="mem_alloc_fail#check", doc_id="mem_alloc_fail", section="Check",
        text="irrelevant for this test", rank=1,
    )
    result = build_fallback([hit], runbook_dir=runbook_dir, tcodes_path=tcodes_path)

    assert result.confidence == "low"
    assert result.category == "memory_dump"
    assert result.sources == ["mem_alloc_fail#check"]
    assert "ST22" in result.tcodes
    assert len(result.steps) >= 1
    assert all(len(step.action) >= 5 for step in result.steps)


def test_fallback_picks_the_lowest_ranked_hit_as_best(fake_corpus):
    runbook_dir, tcodes_path = fake_corpus
    worse = Hit(chunk_id="dialog_timeout#check", doc_id="dialog_timeout", section="Check",
                text="x", rank=2)
    better = Hit(chunk_id="mem_alloc_fail#check", doc_id="mem_alloc_fail", section="Check",
                 text="x", rank=1)
    result = build_fallback([worse, better], runbook_dir=runbook_dir, tcodes_path=tcodes_path)
    assert result.category == "memory_dump"
