import app.llm as llm_module
from app.retrieval.chunk import chunk_by_section
from app.retrieval.runbooks import load_tcodes, parse_runbook
from app.retrieval.store import Store
from app.schemas import IndexManifest
from eval.run_e2e import _run_one_case, category_accuracy, tcode_recall, unverified_claim_rate, valid_output_rate
from eval.schema import EvalCase


def _case(**overrides) -> dict:
    base = dict(
        case_id="t01", gold_category="memory_dump", gold_tcodes=["ST22", "ST02"],
        category_correct=True, tcode_recall=1.0, fell_back=False, unverified_claim=False,
    )
    base.update(overrides)
    return base


def test_category_accuracy_all_correct():
    cases = [_case(), _case(case_id="t02")]
    assert category_accuracy(cases) == 1.0


def test_category_accuracy_half_correct():
    cases = [_case(), _case(case_id="t02", category_correct=False)]
    assert category_accuracy(cases) == 0.5


def test_category_accuracy_empty_is_zero():
    assert category_accuracy([]) == 0.0


def test_tcode_recall_partial():
    cases = [_case(tcode_recall=0.5)]
    assert tcode_recall(cases) == 0.5


def test_tcode_recall_only_averages_over_in_scope_cases():
    cases = [
        _case(gold_tcodes=["ST22"], tcode_recall=1.0),
        _case(case_id="oos", gold_tcodes=[], tcode_recall=0.0),  # out-of-scope, no gold tcodes
    ]
    assert tcode_recall(cases) == 1.0


def test_unverified_claim_rate_counts_flagged_cases():
    cases = [_case(unverified_claim=True), _case(case_id="t02", unverified_claim=False)]
    assert unverified_claim_rate(cases) == 0.5


def test_valid_output_rate_excludes_fallback_cases():
    cases = [_case(fell_back=False), _case(case_id="t02", fell_back=True)]
    assert valid_output_rate(cases) == 0.5


def test_valid_output_rate_empty_is_zero():
    assert valid_output_rate([]) == 0.0


def _store(fake_corpus) -> Store:
    runbook_dir, tcodes_path = fake_corpus
    tcodes = load_tcodes(tcodes_path)
    chunks = []
    for path in sorted(runbook_dir.glob("*.md")):
        runbook = parse_runbook(path, tcodes)
        chunks.extend(chunk_by_section(runbook))
    manifest = IndexManifest(
        corpus_sha="dummy", chunk_strategy="section", embed_model=None, embed_dim=None,
        n_runbooks=3, n_chunks=len(chunks), n_vectors=0, built_at="2026-01-01T00:00:00Z",
        git_commit=None,
    )
    return Store(chunks=chunks, manifest=manifest, embeddings=None, tcodes=tcodes)


def test_unverified_claim_set_by_a_dropped_citation_alone(fake_corpus, monkeypatch):
    """T044: a case whose only problem is a fabricated citation (no out-of-allowlist
    tcode at all) must still be counted by unverified_claim_rate -- not just the
    unverified_tcodes path."""
    store = _store(fake_corpus)
    case = EvalCase(
        id="t01", split="test", format="st22_header", difficulty="easy",
        log="dump says TSV_TNEW_PAGE_ALLOC_FAILED no more storage space for internal table",
        gold_category="memory_dump", gold_docs=["mem_alloc_fail"], acceptable_docs=[],
        gold_tcodes=["ST22"], synthetic=True, notes="",
    )

    def fake_chat(messages, *, tools=None, temperature=0, model=None):
        content = (
            '{"category": "memory_dump", "summary": "short dump", "tcodes": ["ST22"], '
            '"steps": [{"action": "Open ST22 and read the dump.", "tcode": "ST22"}], '
            '"escalate_to": "developer", "sources": ["fabricated#not_real"], "confidence": "high"}'
        )
        return {"choices": [{"message": {"role": "assistant", "content": content, "tool_calls": None}}]}

    monkeypatch.setattr(llm_module, "chat", fake_chat)

    case_result = _run_one_case(case, mode="E-NoRAG", store=store)

    assert case_result["produced"]["unverified_tcodes"] == []  # tcode itself was fine
    assert case_result["unverified_claim"] is True  # but the fabricated citation still counts
    assert unverified_claim_rate([case_result]) == 1.0
