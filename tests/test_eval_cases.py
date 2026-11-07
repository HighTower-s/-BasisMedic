"""SC-001/SC-002/SC-003: the eval set's shape and its independence from the corpus text."""

import pytest

from app.retrieval.runbooks import load_corpus
from eval.schema import (
    EvalSetError,
    check_no_copied_phrasing,
    check_no_cross_split_duplicates,
    load_split,
    validate_split,
)


@pytest.fixture(scope="module")
def corpus_and_cases():
    runbooks, tcodes = load_corpus()
    doc_ids = {r.doc_id for r in runbooks}
    dev = load_split("dev")
    test = load_split("test")
    return runbooks, tcodes, doc_ids, dev, test


def test_dev_split_shape(corpus_and_cases):
    _, tcodes, doc_ids, dev, _ = corpus_and_cases
    assert len(dev) == 10
    validate_split(dev, "dev", tcodes, doc_ids)


def test_test_split_shape(corpus_and_cases):
    _, tcodes, doc_ids, _, test = corpus_and_cases
    assert len(test) == 30
    validate_split(test, "test", tcodes, doc_ids)


def test_every_runbook_covered_by_test_split(corpus_and_cases):
    _, _, doc_ids, _, test = corpus_and_cases
    covered = {doc for c in test for doc in c.gold_docs}
    assert covered == doc_ids


def test_no_cross_split_duplicate_logs(corpus_and_cases):
    _, _, _, dev, test = corpus_and_cases
    check_no_cross_split_duplicates(dev, test)  # must not raise


def test_no_copied_phrasing_from_runbook_analysis(corpus_and_cases):
    runbooks, _, _, dev, test = corpus_and_cases
    sections = {
        f"{r.doc_id}#{name}": body for r in runbooks for name, body in r.sections.items()
    }
    check_no_copied_phrasing(dev + test, sections)  # must not raise


def test_out_of_scope_cases_have_empty_docs_and_tcodes(corpus_and_cases):
    _, _, _, dev, test = corpus_and_cases
    for case in dev + test:
        if case.is_out_of_scope:
            assert case.gold_docs == case.acceptable_docs == case.gold_tcodes == []


# --- the checks must actually fire on a broken set (not just pass by accident) ---


def test_wrong_dev_count_is_rejected(corpus_and_cases):
    _, tcodes, doc_ids, dev, _ = corpus_and_cases
    with pytest.raises(EvalSetError, match="dev split"):
        validate_split(dev[:-1], "dev", tcodes, doc_ids)


def test_missing_runbook_coverage_is_rejected(corpus_and_cases):
    """Redirect every gold reference to rfc_trfc_queue elsewhere, preserving every other
    count, so only the coverage check can fire."""
    _, tcodes, doc_ids, _, test = corpus_and_cases
    retargeted = [
        c.model_copy(update={"gold_docs": ["rfc_connection_failed"]})
        if "rfc_trfc_queue" in c.gold_docs
        else c
        for c in test
    ]
    with pytest.raises(EvalSetError, match="rfc_trfc_queue"):
        validate_split(retargeted, "test", tcodes, doc_ids)


def test_unknown_gold_doc_is_rejected(corpus_and_cases):
    _, tcodes, doc_ids, dev, _ = corpus_and_cases
    bad = dev[0].model_copy(update={"gold_docs": ["not_a_real_runbook"]})
    with pytest.raises(EvalSetError, match="not_a_real_runbook"):
        validate_split([bad, *dev[1:]], "dev", tcodes, doc_ids)


def test_copied_cause_sentence_is_caught():
    from eval.schema import EvalCase

    sections = {
        "x#Cause": "An internal table needed more memory than the work process could reserve "
        "for it right now."
    }
    case = EvalCase(
        id="d01",
        split="dev",
        format="other",
        difficulty="easy",
        log="An internal table needed more memory than the work process could reserve for it.",
        gold_category="memory_dump",
        gold_docs=["x"],
    )
    with pytest.raises(EvalSetError, match="d01"):
        check_no_copied_phrasing([case], sections)


def test_symptoms_overlap_is_not_flagged():
    """The shared error-message text in Symptoms is intentional, per 09_eval_plan.md."""
    from eval.schema import EvalCase

    sections = {"x#Symptoms": "No more storage space available for extending an internal table."}
    case = EvalCase(
        id="d01",
        split="dev",
        format="st22_header",
        difficulty="easy",
        log="No more storage space available for extending an internal table.",
        gold_category="memory_dump",
        gold_docs=["x"],
    )
    check_no_copied_phrasing([case], sections)  # must not raise
