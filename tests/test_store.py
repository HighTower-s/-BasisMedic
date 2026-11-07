import json

import numpy as np
import pytest

from app.retrieval import runbooks
from app.retrieval.store import StaleIndexError, Store


def _write_index(index_dir, chunks, manifest, embeddings=None):
    index_dir.mkdir(parents=True, exist_ok=True)
    with (index_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c) + "\n")
    (index_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    if embeddings is not None:
        np.save(index_dir / "embeddings.npy", embeddings)


def _chunk_dict(doc_id):
    return {
        "chunk_id": f"{doc_id}#symptoms",
        "doc_id": doc_id,
        "category": "memory_dump",
        "section": "Symptoms",
        "title": doc_id,
        "text": "some text",
    }


def test_load_no_embed_manifest_is_valid_for_bm25(tmp_path, fake_corpus):
    runbook_dir, tcodes_path = fake_corpus
    sha = runbooks.corpus_sha(runbook_dir, tcodes_path)
    index_dir = tmp_path / "index"
    chunks = [_chunk_dict("mem_alloc_fail")]
    manifest = {
        "corpus_sha": sha,
        "chunk_strategy": "section",
        "embed_model": None,
        "embed_dim": None,
        "n_runbooks": 3,
        "n_chunks": 1,
        "n_vectors": 0,
        "built_at": "2026-01-01T00:00:00Z",
        "git_commit": None,
    }
    _write_index(index_dir, chunks, manifest)

    store = Store.load(index_dir=index_dir, runbook_dir=runbook_dir, tcodes_path=tcodes_path)
    assert store.embeddings is None
    assert len(store.chunks) == 1


def test_cosine_search_raises_on_no_embed_index(tmp_path, fake_corpus):
    runbook_dir, tcodes_path = fake_corpus
    sha = runbooks.corpus_sha(runbook_dir, tcodes_path)
    index_dir = tmp_path / "index"
    manifest = {
        "corpus_sha": sha,
        "chunk_strategy": "section",
        "embed_model": None,
        "embed_dim": None,
        "n_runbooks": 3,
        "n_chunks": 1,
        "n_vectors": 0,
        "built_at": "2026-01-01T00:00:00Z",
        "git_commit": None,
    }
    _write_index(index_dir, [_chunk_dict("mem_alloc_fail")], manifest)
    store = Store.load(index_dir=index_dir, runbook_dir=runbook_dir, tcodes_path=tcodes_path)

    with pytest.raises(StaleIndexError):
        store.cosine_search(np.zeros(4, dtype=np.float32))


def test_load_raises_on_chunk_embedding_row_misalignment(tmp_path, fake_corpus):
    runbook_dir, tcodes_path = fake_corpus
    sha = runbooks.corpus_sha(runbook_dir, tcodes_path)
    index_dir = tmp_path / "index"
    manifest = {
        "corpus_sha": sha,
        "chunk_strategy": "section",
        "embed_model": "bge-m3",
        "embed_dim": 4,
        "n_runbooks": 3,
        "n_chunks": 1,
        "n_vectors": 2,
        "built_at": "2026-01-01T00:00:00Z",
        "git_commit": None,
    }
    embeddings = np.zeros((2, 4), dtype=np.float32)  # 2 rows but only 1 chunk line
    _write_index(index_dir, [_chunk_dict("mem_alloc_fail")], manifest, embeddings)

    with pytest.raises(StaleIndexError):
        Store.load(index_dir=index_dir, runbook_dir=runbook_dir, tcodes_path=tcodes_path)


def test_load_raises_stale_index_error_on_corpus_sha_mismatch(tmp_path, fake_corpus):
    runbook_dir, tcodes_path = fake_corpus
    index_dir = tmp_path / "index"
    manifest = {
        "corpus_sha": "not-the-real-sha",
        "chunk_strategy": "section",
        "embed_model": None,
        "embed_dim": None,
        "n_runbooks": 3,
        "n_chunks": 1,
        "n_vectors": 0,
        "built_at": "2026-01-01T00:00:00Z",
        "git_commit": None,
    }
    _write_index(index_dir, [_chunk_dict("mem_alloc_fail")], manifest)

    with pytest.raises(StaleIndexError):
        Store.load(index_dir=index_dir, runbook_dir=runbook_dir, tcodes_path=tcodes_path)


def test_load_raises_when_no_index_present(tmp_path, fake_corpus):
    runbook_dir, tcodes_path = fake_corpus
    with pytest.raises(StaleIndexError):
        Store.load(index_dir=tmp_path / "missing", runbook_dir=runbook_dir, tcodes_path=tcodes_path)
