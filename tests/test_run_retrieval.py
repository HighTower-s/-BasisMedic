import pytest

from app.retrieval.store import Store
from eval.run_retrieval import run_config


@pytest.fixture
def real_store():
    return Store.load()


def test_run_config_rejects_chunk_strategy_mismatch(real_store):
    with pytest.raises(ValueError):
        run_config(
            split="dev",
            mode="bm25",
            chunk_strategy="fixed",
            min_score=0.40,
            experiment="T", name="t",
            store=real_store,
        )


def test_repeated_runs_on_dev_split_are_identical(real_store):
    first = run_config(
        split="dev", mode="bm25", chunk_strategy="section", min_score=0.40,
        experiment="T", name="t", store=real_store,
    )
    second = run_config(
        split="dev", mode="bm25", chunk_strategy="section", min_score=0.40,
        experiment="T", name="t", store=real_store,
    )
    assert first["aggregate"] == second["aggregate"]
