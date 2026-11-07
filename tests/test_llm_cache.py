import pytest

import app.llm as llm_module
from app.llm import UpstreamError, embed_with_cache_stats


class _Item:
    def __init__(self, index, embedding):
        self.index = index
        self.embedding = embedding


class _Response:
    def __init__(self, data):
        self.data = data


class _FakeClient:
    def __init__(self, vector_for=None, fail=False):
        self.calls = []
        self._vector_for = vector_for or (lambda text: [0.1] * 1024)
        self._fail = fail

        class _Embeddings:
            def create(inner_self, model, input):
                self.calls.append(list(input))
                if self._fail:
                    raise RuntimeError("gateway unreachable")
                return _Response(
                    [_Item(i, self._vector_for(text)) for i, text in enumerate(input)]
                )

        self.embeddings = _Embeddings()


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_module.config, "CACHE_DIR", tmp_path / "cache")


def test_embed_preserves_input_order(monkeypatch):
    fake = _FakeClient(vector_for=lambda text: [float(ord(text[0]))] * 1024)
    monkeypatch.setattr(llm_module, "_client", lambda: fake)

    vectors, hits, misses = embed_with_cache_stats(["b text", "a text"], model="bge-m3")

    assert vectors[0][0] == float(ord("b"))
    assert vectors[1][0] == float(ord("a"))
    assert hits == 0
    assert misses == 2


def test_embed_asserts_vector_dimension(monkeypatch):
    fake = _FakeClient(vector_for=lambda text: [0.1] * 7)
    monkeypatch.setattr(llm_module, "_client", lambda: fake)

    with pytest.raises(UpstreamError):
        embed_with_cache_stats(["one text here"], model="bge-m3")


def test_embed_batches_all_texts_in_one_call(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(llm_module, "_client", lambda: fake)

    embed_with_cache_stats(["text one", "text two", "text three"], model="bge-m3")

    assert len(fake.calls) == 1
    assert len(fake.calls[0]) == 3


def test_second_call_is_served_entirely_from_cache(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(llm_module, "_client", lambda: fake)

    embed_with_cache_stats(["repeat this text"], model="bge-m3")
    assert len(fake.calls) == 1

    vectors, hits, misses = embed_with_cache_stats(["repeat this text"], model="bge-m3")
    assert len(fake.calls) == 1  # no new gateway call
    assert hits == 1
    assert misses == 0


def test_gateway_failure_surfaces_as_upstream_error(monkeypatch):
    fake = _FakeClient(fail=True)
    monkeypatch.setattr(llm_module, "_client", lambda: fake)

    with pytest.raises(UpstreamError):
        embed_with_cache_stats(["some text"], model="bge-m3")
