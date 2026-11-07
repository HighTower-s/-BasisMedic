import pytest

import eval.run_all as run_all_module


def test_run_e4_rejects_rows_that_disagree_on_split(monkeypatch):
    def fake_run_e2e_config(*, split, mode, name):
        # agent row claims a different split than the other two -- a real bug this
        # guard must catch.
        fake_split = "dev" if mode == "agent" else "test"
        return {
            "config": {"experiment": "E4", "name": name, "split": fake_split, "baseline": mode,
                       "corpus_sha": "same-sha"},
            "aggregate": {}, "cases": [],
        }

    monkeypatch.setattr(run_all_module, "run_e2e_config", fake_run_e2e_config)
    monkeypatch.setattr(run_all_module, "write_e2e_result", lambda *a, **k: None)

    with pytest.raises(ValueError):
        run_all_module.run_e4()


def test_run_e4_rejects_rows_that_disagree_on_corpus_sha(monkeypatch):
    def fake_run_e2e_config(*, split, mode, name):
        fake_sha = "sha-a" if mode == "agent" else "sha-b"
        return {
            "config": {"experiment": "E4", "name": name, "split": "test", "baseline": mode,
                       "corpus_sha": fake_sha},
            "aggregate": {}, "cases": [],
        }

    monkeypatch.setattr(run_all_module, "run_e2e_config", fake_run_e2e_config)
    monkeypatch.setattr(run_all_module, "write_e2e_result", lambda *a, **k: None)

    with pytest.raises(ValueError):
        run_all_module.run_e4()
