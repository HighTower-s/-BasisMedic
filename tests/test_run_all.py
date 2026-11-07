import pytest

from eval.run_all import _assert_comparable


def _row(split: str, corpus_sha: str) -> dict:
    return {"config": {"split": split, "corpus_sha": corpus_sha}}


def test_assert_comparable_accepts_same_split_and_sha():
    rows = [_row("test", "abc"), _row("test", "abc")]
    _assert_comparable(rows)  # must not raise


def test_assert_comparable_rejects_mixed_splits():
    rows = [_row("dev", "abc"), _row("test", "abc")]
    with pytest.raises(ValueError):
        _assert_comparable(rows)


def test_assert_comparable_rejects_mixed_corpus_sha():
    rows = [_row("test", "abc"), _row("test", "def")]
    with pytest.raises(ValueError):
        _assert_comparable(rows)
