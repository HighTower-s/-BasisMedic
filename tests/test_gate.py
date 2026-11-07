import json

import pytest

from app.retrieval.chunk import chunk_by_section
from app.retrieval.runbooks import load_tcodes, parse_runbook
from app.retrieval.search import InvalidQueryError, search
from app.retrieval.store import Store
from app.schemas import IndexManifest


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
