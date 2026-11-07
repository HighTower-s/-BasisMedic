"""FR-041/SC-009: the min_score sweep must be mechanically unable to touch the test split."""

import pytest

from eval.run_all import sweep_min_score


def test_sweep_min_score_raises_for_test_split():
    with pytest.raises(ValueError):
        sweep_min_score("test", mode="bm25", chunk_strategy="section")


def test_sweep_min_score_raises_for_any_non_dev_split():
    with pytest.raises(ValueError):
        sweep_min_score("nonsense", mode="bm25", chunk_strategy="section")


def test_sweep_min_score_source_never_references_cases_test(tmp_path):
    import inspect

    import eval.run_all as run_all_module

    source = inspect.getsource(run_all_module.sweep_min_score)
    assert "cases_test" not in source
    assert '"test"' not in source  # the only split literal used inside is "dev"
