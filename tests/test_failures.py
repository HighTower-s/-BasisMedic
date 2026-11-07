from eval.run_retrieval import classify_failure
from eval.schema import EvalCase


def _in_scope_case(**overrides) -> EvalCase:
    base = dict(
        id="t01", split="test", format="st22_header", difficulty="easy",
        log="Dump TSV_TNEW_PAGE_ALLOC_FAILED no more storage space for internal table",
        gold_category="memory_dump", gold_docs=["runbook_a"], acceptable_docs=["runbook_b"],
        gold_tcodes=[], synthetic=True, notes="test case",
    )
    base.update(overrides)
    return EvalCase(**base)


def _oos_case(**overrides) -> EvalCase:
    base = dict(
        id="t02", split="test", format="hana_alert", difficulty="medium",
        log="HANA log volume is almost completely full and backups are failing today",
        gold_category="out_of_scope", gold_docs=[], acceptable_docs=[], gold_tcodes=[],
        synthetic=True, notes="oos case",
    )
    base.update(overrides)
    return EvalCase(**base)


def test_retrieving_only_acceptable_doc_is_retrieval_miss():
    case = _in_scope_case()
    cr = {"gated_out": False, "recall_at_k_post": 0.0, "retrieved": [{"doc_id": "runbook_b"}]}
    assert classify_failure(case, cr) == "retrieval_miss"


def test_matching_acceptable_alongside_gold_is_never_a_failure():
    case = _in_scope_case()
    cr = {
        "gated_out": False, "recall_at_k_post": 1.0,
        "retrieved": [{"doc_id": "runbook_a"}, {"doc_id": "runbook_b"}],
    }
    assert classify_failure(case, cr) is None


def test_in_scope_false_refusal_is_gate_false_refusal():
    case = _in_scope_case()
    cr = {"gated_out": True, "recall_at_k_post": None, "retrieved": []}
    assert classify_failure(case, cr) == "gate_false_refusal"


def test_mixed_case_partial_recall():
    case = _in_scope_case(gold_docs=["runbook_a", "runbook_c"], acceptable_docs=[])
    cr = {
        "gated_out": False, "recall_at_k_post": 0.5,
        "retrieved": [{"doc_id": "runbook_a"}],
    }
    assert classify_failure(case, cr) == "partial_recall"


def test_out_of_scope_correctly_gated_out_is_not_a_failure():
    case = _oos_case()
    cr = {"gated_out": True, "recall_at_k_post": None, "retrieved": []}
    assert classify_failure(case, cr) is None


def test_out_of_scope_not_gated_out_is_gate_missed_oos():
    case = _oos_case()
    cr = {"gated_out": False, "recall_at_k_post": None, "retrieved": [{"doc_id": "runbook_a"}]}
    assert classify_failure(case, cr) == "gate_missed_oos"
