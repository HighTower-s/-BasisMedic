from eval.run_all import _render_verdict_and_limitations


def _row(mode: str, recall: float, split: str = "test") -> dict:
    return {"config": {"mode": mode, "split": split}, "aggregate": {"recall_at_3_pre": recall}}


def _baselines(bm25: float, dense_naive: float) -> dict:
    return {
        "R-BM25": {"test": {"aggregate": {"recall_at_3_pre": bm25}}},
        "R-Dense-naive": {"test": {"aggregate": {"recall_at_3_pre": dense_naive}}},
    }


def test_verdict_states_hybrid_wins_when_it_beats_both_baselines():
    rows = [_row("bm25", 0.80), _row("dense", 0.85), _row("hybrid", 0.95)]
    text = _render_verdict_and_limitations(rows, _baselines(0.80, 0.85), n_failures=2)
    assert "beats both named baselines" in text
    assert "does **not** beat" not in text


def test_verdict_states_plainly_when_hybrid_loses_to_a_baseline():
    rows = [_row("bm25", 0.80), _row("dense", 0.90), _row("hybrid", 0.85)]
    text = _render_verdict_and_limitations(rows, _baselines(0.80, 0.90), n_failures=3)
    assert "does **not** beat" in text
