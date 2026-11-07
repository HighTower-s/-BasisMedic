import json

import numpy as np
import pytest

import app.llm as llm_module
from app.retrieval.chunk import chunk_by_section
from app.retrieval.runbooks import load_tcodes, parse_runbook
from app.retrieval.search import InvalidQueryError, search
from app.retrieval.store import Store
from app.schemas import Chunk, IndexManifest


def _store(fake_corpus) -> Store:
    runbook_dir, tcodes_path = fake_corpus
    tcodes = load_tcodes(tcodes_path)
    chunks = []
    for path in sorted(runbook_dir.glob("*.md")):
        runbook = parse_runbook(path, tcodes)
        chunks.extend(chunk_by_section(runbook))
    manifest = IndexManifest(
        corpus_sha="dummy",
        chunk_strategy="section",
        embed_model=None,
        embed_dim=None,
        n_runbooks=3,
        n_chunks=len(chunks),
        n_vectors=0,
        built_at="2026-01-01T00:00:00Z",
        git_commit=None,
    )
    return Store(chunks=chunks, manifest=manifest, embeddings=None, tcodes=tcodes)


def test_bm25_gate_returns_empty_when_no_rare_token(fake_corpus):
    store = _store(fake_corpus)
    hits = search("the user reported a general system issue today", mode="bm25", k=3, min_score=0.4, store=store)
    assert hits == []


def test_bm25_gate_admits_results_with_a_rare_token(fake_corpus):
    store = _store(fake_corpus)
    hits = search(
        "dump says TSV_TNEW_PAGE_ALLOC_FAILED no more storage space",
        mode="bm25",
        k=3,
        min_score=0.4,
        store=store,
    )
    assert len(hits) >= 1
    assert all(h.doc_id for h in hits)
    assert len({h.doc_id for h in hits}) == len(hits)  # distinct docs


def test_bm25_gate_never_consults_min_score(fake_corpus):
    store = _store(fake_corpus)
    query = "dump says TSV_TNEW_PAGE_ALLOC_FAILED no more storage space"
    low = search(query, mode="bm25", k=3, min_score=0.0, store=store)
    high = search(query, mode="bm25", k=3, min_score=0.99, store=store)
    assert len(high) <= len(low)
    assert [h.chunk_id for h in low] == [h.chunk_id for h in high]


def test_invalid_query_too_short_raises(fake_corpus):
    store = _store(fake_corpus)
    with pytest.raises(InvalidQueryError):
        search("short", mode="bm25", store=store)


def test_invalid_query_whitespace_only_raises(fake_corpus):
    store = _store(fake_corpus)
    with pytest.raises(InvalidQueryError):
        search("            ", mode="bm25", store=store)


def _two_chunk_dense_store():
    """Two chunks with hand-picked unit vectors so cosine similarity is exact."""
    chunk_a = Chunk(
        chunk_id="mem_alloc_fail#symptoms", doc_id="mem_alloc_fail", category="memory_dump",
        section="Symptoms", title="mem_alloc_fail", text="TSV_TNEW_PAGE_ALLOC_FAILED dump text",
    )
    chunk_b = Chunk(
        chunk_id="stale_lock#symptoms", doc_id="stale_lock", category="lock_issue",
        section="Symptoms", title="stale_lock", text="a document is locked by SM12",
    )
    matrix = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    manifest = IndexManifest(
        corpus_sha="dummy", chunk_strategy="section", embed_model="test", embed_dim=2,
        n_runbooks=2, n_chunks=2, n_vectors=2, built_at="2026-01-01T00:00:00Z", git_commit=None,
    )
    tcodes = {"SM12": "Lock Entries - display and delete SAP enqueue locks"}
    return Store(chunks=[chunk_a, chunk_b], manifest=manifest, embeddings=matrix, tcodes=tcodes)


def _patch_embed(monkeypatch, vector: list[float]) -> None:
    monkeypatch.setattr(llm_module, "embed", lambda texts, model=None: [vector for _ in texts])


def test_dense_gate_low_cosine_and_no_rare_token_returns_empty(monkeypatch):
    store = _two_chunk_dense_store()
    _patch_embed(monkeypatch, [-1.0, 0.0])  # opposite of chunk_a, orthogonal-ish to chunk_b
    hits = search(
        "the system reported a general issue with no specific code",
        mode="dense", k=3, min_score=0.5, store=store,
    )
    assert hits == []


def test_dense_gate_low_cosine_but_rare_token_admits_results(monkeypatch):
    store = _two_chunk_dense_store()
    _patch_embed(monkeypatch, [-1.0, 0.0])
    hits = search(
        "please check SM12 right away for the issue",
        mode="dense", k=3, min_score=0.5, store=store,
    )
    assert len(hits) >= 1


def test_dense_gate_high_cosine_admits_regardless_of_rare_tokens(monkeypatch):
    store = _two_chunk_dense_store()
    _patch_embed(monkeypatch, [1.0, 0.0])  # matches chunk_a exactly
    hits = search(
        "a completely generic query with no special terms at all",
        mode="dense", k=3, min_score=0.9, store=store,
    )
    assert len(hits) >= 1
    assert hits[0].doc_id == "mem_alloc_fail"
    assert hits[0].dense_score == pytest.approx(1.0)


def test_hybrid_gate_reads_dense_score_not_fused_score(monkeypatch):
    store = _two_chunk_dense_store()
    _patch_embed(monkeypatch, [1.0, 0.0])
    hits = search(
        "a completely generic query with no special terms at all",
        mode="hybrid", k=3, min_score=0.9, store=store,
    )
    assert len(hits) >= 1
    assert hits[0].dense_score == pytest.approx(1.0)
    assert hits[0].fused_score is not None
