"""Hand-computed fixtures for recall@k, MRR, and the two gate rates."""

import pytest

from eval.metrics import false_refusal_rate, gate_accuracy, mrr, recall_at_k


def test_recall_gold_at_rank_1():
    assert recall_at_k(["a", "b", "c"], ["a"]) == 1.0


def test_recall_gold_at_rank_3():
    assert recall_at_k(["x", "y", "a"], ["a"]) == 1.0


def test_recall_gold_absent():
    assert recall_at_k(["x", "y", "z"], ["a"]) == 0.0


def test_recall_partial_for_mixed_case_two_golds():
    assert recall_at_k(["a", "x", "y"], ["a", "b"]) == 0.5


def test_recall_empty_ranked_list():
    assert recall_at_k([], ["a"]) == 0.0


def test_recall_acceptable_doc_earns_no_credit():
    # acceptable_docs are never passed as relevant_docs - caller's responsibility (FR-034).
    assert recall_at_k(["b"], ["a"]) == 0.0


def test_recall_requires_nonempty_relevant():
    with pytest.raises(ValueError):
        recall_at_k(["a"], [])


def test_mrr_gold_at_rank_1():
    assert mrr(["a", "b"], ["a"]) == 1.0


def test_mrr_gold_at_rank_2():
    assert mrr(["x", "a"], ["a"]) == 0.5


def test_mrr_gold_at_rank_3():
    assert mrr(["x", "y", "a"], ["a"]) == pytest.approx(1 / 3)


def test_mrr_gold_absent_is_zero():
    assert mrr(["x", "y"], ["a"]) == 0.0


def test_mrr_empty_ranked_list():
    assert mrr([], ["a"]) == 0.0


def test_mrr_first_of_multiple_golds_wins():
    assert mrr(["x", "b", "a"], ["a", "b"]) == 0.5


def test_gate_accuracy_all_correctly_rejected():
    assert gate_accuracy([True, True, True]) == 1.0


def test_gate_accuracy_none_rejected():
    assert gate_accuracy([False, False]) == 0.0


def test_gate_accuracy_partial():
    assert gate_accuracy([True, False, True, False]) == 0.5


def test_gate_accuracy_empty_population():
    assert gate_accuracy([]) == 0.0


def test_false_refusal_rate_none_wrongly_rejected():
    assert false_refusal_rate([False, False, False]) == 0.0


def test_false_refusal_rate_some_wrongly_rejected():
    assert false_refusal_rate([True, False, False, False]) == 0.25
