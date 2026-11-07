import json

import app.llm as llm_module
from app.agent.formatter import format_result
from app.schemas import Hit


def _evidence() -> list[Hit]:
    return [
        Hit(chunk_id="mem_tsv_tnew_page_alloc#check", doc_id="mem_tsv_tnew_page_alloc",
            section="Check", text="ST22 - open the dump", rank=1),
    ]


def _chat_response(content: str) -> dict:
    return {"choices": [{"message": {"role": "assistant", "content": content, "tool_calls": None}}]}


def test_well_formed_json_on_first_attempt_needs_no_repair(monkeypatch):
    valid = {
        "category": "memory_dump",
        "summary": "short dump",
        "tcodes": ["ST22"],
        "steps": [{"action": "Open ST22 and read the dump.", "tcode": "ST22"}],
        "escalate_to": "developer",
        "sources": ["mem_tsv_tnew_page_alloc#check"],
        "confidence": "high",
    }
    calls = []

    def fake_chat(messages, *, tools=None, temperature=0, model=None):
        calls.append(messages)
        return _chat_response(json.dumps(valid))

    monkeypatch.setattr(llm_module, "chat", fake_chat)

    result = format_result(_evidence(), "a log")
    assert result.category == "memory_dump"
    assert len(calls) == 1  # no repair attempt needed
