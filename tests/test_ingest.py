"""Integration tests for build_index against the real corpus, offline (--no-embed)."""

import shutil

import pytest

from app.retrieval.ingest import build_index
from app.retrieval.store import StaleIndexError, Store


def test_build_index_offline_produces_a_loadable_bm25_store(tmp_path):
    index_dir = tmp_path / "index"
    manifest, n_tcodes, hits, misses = build_index(strategy="section", embed=False, index_dir=index_dir)

    assert manifest.n_runbooks == 16
    assert manifest.n_chunks == 96
    assert manifest.n_vectors == 0
    assert n_tcodes > 0

    store = Store.load(index_dir=index_dir)
    assert len(store.chunks) == 96
    assert store.embeddings is None


def test_rebuilding_twice_is_byte_identical(tmp_path):
    index_dir = tmp_path / "index"
    build_index(strategy="section", embed=False, index_dir=index_dir)
    first = (index_dir / "chunks.jsonl").read_text(encoding="utf-8")
    build_index(strategy="section", embed=False, index_dir=index_dir)
    second = (index_dir / "chunks.jsonl").read_text(encoding="utf-8")
    assert first == second


def test_stale_index_detected_after_runbook_edit(tmp_path):
    corpus_copy = tmp_path / "runbooks"
    shutil.copytree("data/runbooks", corpus_copy)
    tcodes_copy = tmp_path / "tcodes.json"
    shutil.copy("data/tcodes.json", tcodes_copy)
    index_dir = tmp_path / "index"

    from app.retrieval import ingest as ingest_module
    from app.retrieval import runbooks as runbooks_module

    original_sha = runbooks_module.corpus_sha
    runbooks_module.corpus_sha = lambda *a, **k: original_sha(corpus_copy, tcodes_copy)
    try:
        build_index(strategy="section", embed=False, index_dir=index_dir)
        # edit a runbook after the index was built
        target = next(corpus_copy.glob("*.md"))
        target.write_text(target.read_text(encoding="utf-8") + "\n<!-- edited -->", encoding="utf-8")

        with pytest.raises(StaleIndexError):
            Store.load(index_dir=index_dir, runbook_dir=corpus_copy, tcodes_path=tcodes_copy)
    finally:
        runbooks_module.corpus_sha = original_sha
