from app.agent.tools import TOOLS, lookup_tcode, search_runbook
from app.retrieval.chunk import chunk_by_section
from app.retrieval.runbooks import load_tcodes, parse_runbook
from app.schemas import IndexManifest
from app.retrieval.store import Store


def _store(fake_corpus) -> Store:
    runbook_dir, tcodes_path = fake_corpus
    tcodes = load_tcodes(tcodes_path)
    chunks = []
    for path in sorted(runbook_dir.glob("*.md")):
        runbook = parse_runbook(path, tcodes)
        chunks.extend(chunk_by_section(runbook))
    manifest = IndexManifest(
        corpus_sha="dummy", chunk_strategy="section", embed_model=None, embed_dim=None,
        n_runbooks=3, n_chunks=len(chunks), n_vectors=0, built_at="2026-01-01T00:00:00Z",
        git_commit=None,
    )
    return Store(chunks=chunks, manifest=manifest, embeddings=None, tcodes=tcodes)


def test_search_runbook_rejects_short_query(fake_corpus):
    store = _store(fake_corpus)
    text, hits = search_runbook({"query": "short"}, store=store)
    assert hits == []
    assert "error" in text.lower()


def test_search_runbook_returns_no_relevant_runbook_sentinel(fake_corpus):
    store = _store(fake_corpus)
    text, hits = search_runbook({"query": "the general system issue reported today"}, mode="bm25", store=store)
    assert text == "NO_RELEVANT_RUNBOOK"
    assert hits == []


def test_search_runbook_returns_hits_and_text_for_a_real_match(fake_corpus):
    store = _store(fake_corpus)
    text, hits = search_runbook(
        {"query": "dump says TSV_TNEW_PAGE_ALLOC_FAILED no more storage space"},
        mode="bm25", store=store,
    )
    assert len(hits) >= 1
    assert hits[0].doc_id
    assert hits[0].chunk_id in text


def test_lookup_tcode_known_code(fake_corpus):
    store = _store(fake_corpus)
    text = lookup_tcode({"code": "SM12"}, store=store)
    assert "Lock Entries" in text


def test_lookup_tcode_unknown_code(fake_corpus):
    store = _store(fake_corpus)
    text = lookup_tcode({"code": "ZZ99"}, store=store)
    assert text == "unknown tcode"


def test_lookup_tcode_malformed_code(fake_corpus):
    store = _store(fake_corpus)
    text = lookup_tcode({"code": "not a code!"}, store=store)
    assert "error" in text.lower()


def test_tools_registry_only_has_the_two_allowed_tools():
    assert set(TOOLS) == {"search_runbook", "lookup_tcode"}
