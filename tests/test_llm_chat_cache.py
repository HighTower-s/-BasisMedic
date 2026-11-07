import json
from types import SimpleNamespace

import pytest

import app.llm as llm_module
from app.llm import UpstreamError, chat


def _fake_response(content="hello"):
    return SimpleNamespace(
        model_dump=lambda: {
            "choices": [{"message": {"role": "assistant", "content": content, "tool_calls": None}}]
        }
    )


class _FakeCompletions:
    def __init__(self, calls: list, response=None, raise_exc: Exception | None = None):
        self.calls = calls
        self._response = response or _fake_response()
        self._raise = raise_exc

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._raise:
            raise self._raise
        return self._response


class _FakeChat:
    def __init__(self, completions):
        self.completions = completions


class _FakeClient:
    def __init__(self, completions):
        self.chat = _FakeChat(completions)


@pytest.fixture
def chat_cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_module.config, "CHAT_CACHE_DIR", tmp_path)
    return tmp_path


def test_cache_miss_calls_client_and_writes_cache(chat_cache_dir, monkeypatch):
    calls = []
    client = _FakeClient(_FakeCompletions(calls))
    monkeypatch.setattr(llm_module, "_client", lambda: client)

    result = chat([{"role": "user", "content": "hi"}], model="test-model")

    assert len(calls) == 1
    assert result["choices"][0]["message"]["content"] == "hello"
    assert len(list(chat_cache_dir.glob("*.json"))) == 1


def test_identical_call_is_served_from_cache(chat_cache_dir, monkeypatch):
    calls = []
    client = _FakeClient(_FakeCompletions(calls))
    monkeypatch.setattr(llm_module, "_client", lambda: client)

    messages = [{"role": "user", "content": "hi"}]
    chat(messages, model="test-model")
    chat(messages, model="test-model")

    assert len(calls) == 1  # second call never hit the client


def test_different_tools_is_a_cache_miss(chat_cache_dir, monkeypatch):
    calls = []
    client = _FakeClient(_FakeCompletions(calls))
    monkeypatch.setattr(llm_module, "_client", lambda: client)

    messages = [{"role": "user", "content": "hi"}]
    chat(messages, model="test-model", tools=None)
    chat(messages, model="test-model", tools=[{"type": "function", "function": {"name": "x"}}])

    assert len(calls) == 2


def test_different_temperature_is_a_cache_miss(chat_cache_dir, monkeypatch):
    calls = []
    client = _FakeClient(_FakeCompletions(calls))
    monkeypatch.setattr(llm_module, "_client", lambda: client)

    messages = [{"role": "user", "content": "hi"}]
    chat(messages, model="test-model", temperature=0)
    chat(messages, model="test-model", temperature=0.5)

    assert len(calls) == 2


def test_gateway_error_raises_upstream_error(chat_cache_dir, monkeypatch):
    calls = []
    client = _FakeClient(_FakeCompletions(calls, raise_exc=RuntimeError("boom")))
    monkeypatch.setattr(llm_module, "_client", lambda: client)

    with pytest.raises(UpstreamError):
        chat([{"role": "user", "content": "hi"}], model="test-model")
