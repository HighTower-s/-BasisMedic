"""FR-010/SC-005: every returned citation resolves to real corpus text, across both splits."""

from app.retrieval.store import Store
from eval.run_retrieval import run_config


def test_zero_dangling_citations_across_dev_and_test_splits():
    store = Store.load()
    for split in ("dev", "test"):
        result = run_config(
            split=split, mode="bm25", chunk_strategy="section", min_score=0.40,
            experiment="citation-check", name="citation-check", store=store,
        )
        known_ids = {c.chunk_id for c in store.chunks}
        for case in result["cases"]:
            for item in case["retrieved"]:
                assert item["chunk_id"] in known_ids
