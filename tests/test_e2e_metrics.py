from eval.run_e2e import category_accuracy, tcode_recall, unverified_claim_rate, valid_output_rate


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
