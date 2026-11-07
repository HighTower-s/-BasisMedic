import app.llm as llm_module
from app.retrieval.chunk import chunk_by_section
from app.retrieval.runbooks import load_tcodes, parse_runbook
from app.retrieval.store import Store
from app.schemas import IndexManifest
from app.triage_service import triage


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


def _tool_call_message(call_id, name, arguments):
    return {
        "role": "assistant", "content": None,
        "tool_calls": [{"id": call_id, "function": {"name": name, "arguments": arguments}}],
    }


def _no_tool_call_message(content="diagnosis"):
    return {"role": "assistant", "content": content, "tool_calls": None}


def _response(message):
    return {"choices": [{"message": message}]}


def test_out_of_scope_is_forced_when_evidence_is_empty(fake_corpus, monkeypatch):
    store = _store(fake_corpus)
    responses = [
        _response(_tool_call_message(
            "c1", "search_runbook", '{"query": "a completely unrelated generic issue today"}',
        )),
        _response(_no_tool_call_message("I think this is a memory_dump issue.")),
        # Phase 2 formatter MUST NOT be called -- if it is, this third response (malformed)
        # would be consumed and the test would fail differently, proving the skip.
        _response(_no_tool_call_message("{}")),
    ]
    calls = {"count": 0}

    def fake_chat(messages, *, tools=None, temperature=0, model=None):
        calls["count"] += 1
        return responses.pop(0)

    monkeypatch.setattr(llm_module, "chat", fake_chat)

    result = triage("a log with no matching runbook content at all here", store=store, mode="agent", retrieval_mode="bm25")

    assert result.category == "out_of_scope"
    assert result.tcodes == []
    assert result.sources == []
    assert calls["count"] == 2  # only the two Phase-1 loop calls; formatter skipped


def test_multi_search_case_not_forced_when_a_later_call_finds_something(fake_corpus, monkeypatch):
    store = _store(fake_corpus)
    responses = [
        _response(_tool_call_message(
            "c1", "search_runbook", '{"query": "a completely unrelated generic issue today"}',
        )),
        _response(_tool_call_message(
            "c2", "search_runbook",
            '{"query": "dump says TSV_TNEW_PAGE_ALLOC_FAILED no more storage space"}',
        )),
        _response(_no_tool_call_message()),
        _response(_no_tool_call_message(
            '{"category": "memory_dump", "summary": "short dump", "tcodes": ["ST22"], '
            '"steps": [{"action": "Open ST22 and read the dump.", "tcode": "ST22"}], '
            '"escalate_to": "developer", "sources": ["mem_alloc_fail#check"], "confidence": "high"}'
        )),
    ]

    def fake_chat(messages, *, tools=None, temperature=0, model=None):
        return responses.pop(0)

    monkeypatch.setattr(llm_module, "chat", fake_chat)

    result = triage("a log that needs two searches to resolve correctly", store=store, mode="agent", retrieval_mode="bm25")

    assert result.category == "memory_dump"
