import app.llm as llm_module
from app.agent.loop import gather_evidence
from app.retrieval.chunk import chunk_by_section
from app.retrieval.runbooks import load_tcodes, parse_runbook
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
        corpus_sha="dummy", chunk_strategy="section", embed_model=None, embed_dim=None,
        n_runbooks=3, n_chunks=len(chunks), n_vectors=0, built_at="2026-01-01T00:00:00Z",
        git_commit=None,
    )
    return Store(chunks=chunks, manifest=manifest, embeddings=None, tcodes=tcodes)


def _tool_call_message(call_id, name, arguments):
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": call_id, "function": {"name": name, "arguments": arguments}}
        ],
    }


def _no_tool_call_message(content="diagnosis text"):
    return {"role": "assistant", "content": content, "tool_calls": None}


def _response(message):
    return {"choices": [{"message": message}]}


def test_natural_stop_ends_loop_after_one_search(fake_corpus, monkeypatch):
    store = _store(fake_corpus)
    responses = [
        _response(_tool_call_message(
            "c1", "search_runbook",
            '{"query": "dump says TSV_TNEW_PAGE_ALLOC_FAILED no more storage space"}',
        )),
        _response(_no_tool_call_message()),
    ]

    def fake_chat(messages, *, tools=None, temperature=0, model=None):
        return responses.pop(0)

    monkeypatch.setattr(llm_module, "chat", fake_chat)

    records = gather_evidence("a log", store=store, max_steps=5, mode="bm25")
    assert len(records) == 1
    assert records[0].tool == "search_runbook"
    assert len(records[0].hits) >= 1
