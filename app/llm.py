"""The ONLY module in the project that calls the gateway (Constitution VI).
Wraps openai.embeddings.create with a disk cache keyed by sha256(model|text) so repeated
runs are both free and bit-identical (R-09, FR-036, SC-004). Also the only caller of
chat completions (Feature 2), cached the same way (specs/002-triage-agent/research.md R-09)."""

import hashlib
import json
from pathlib import Path

from openai import OpenAI

from app import config

EMBED_DIM = 1024


class UpstreamError(Exception):
    """The gateway failed, timed out, or returned something that cannot be trusted."""


def _cache_path(model: str, text: str) -> Path:
    key = hashlib.sha256(f"{model}|{text}".encode("utf-8")).hexdigest()
    return config.CACHE_DIR / f"{key}.json"


def _cache_get(model: str, text: str) -> list[float] | None:
    path = _cache_path(model, text)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data.get("vector")


def _cache_put(model: str, text: str, vector: list[float]) -> None:
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(model, text)
    path.write_text(json.dumps({"model": model, "dim": len(vector), "vector": vector}), encoding="utf-8")


def _client() -> OpenAI:
    return OpenAI(base_url=config.base_url(), api_key=config.api_key())


def embed(texts: list[str], model: str | None = None) -> list[list[float]]:
    vectors, _hits, _misses = embed_with_cache_stats(texts, model=model)
    return vectors


def embed_with_cache_stats(
    texts: list[str], model: str | None = None
) -> tuple[list[list[float]], int, int]:
    """Returns (vectors, cache_hits, cache_misses). vectors[i] corresponds to texts[i]."""
    model = model or config.embed_model()
    results: list[list[float] | None] = [None] * len(texts)
    to_fetch: list[tuple[int, str]] = []

    for i, text in enumerate(texts):
        cached = _cache_get(model, text)
        if cached is not None:
            results[i] = cached
        else:
            to_fetch.append((i, text))

    hits = len(texts) - len(to_fetch)
    misses = len(to_fetch)

    if to_fetch:
        try:
            client = _client()
            response = client.embeddings.create(model=model, input=[t for _, t in to_fetch])
        except Exception as exc:
            raise UpstreamError(f"embedding call to {model!r} failed: {exc}") from exc

        by_local_index = {item.index: item for item in response.data}
        if len(by_local_index) != len(to_fetch):
            raise UpstreamError(
                f"gateway returned {len(by_local_index)} vectors for {len(to_fetch)} inputs"
            )

        for local_index, (i, text) in enumerate(to_fetch):
            item = by_local_index.get(local_index)
            if item is None:
                raise UpstreamError(f"gateway response missing embedding at index {local_index}")
            vector = list(item.embedding)
            if len(vector) != EMBED_DIM:
                raise UpstreamError(f"expected a {EMBED_DIM}-dim vector, got {len(vector)}")
            results[i] = vector
            _cache_put(model, text, vector)

    assert all(r is not None for r in results)
    return results, hits, misses  # type: ignore[return-value]


def _chat_cache_key(model: str, temperature: float, messages: list[dict], tools: list[dict] | None) -> str:
    payload = json.dumps(
        {
            "model": model,
            "temperature": temperature,
            "messages": messages,
            "tools": tools or [],
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _chat_cache_path(key: str) -> Path:
    return config.CHAT_CACHE_DIR / f"{key}.json"


def _chat_cache_get(key: str) -> dict | None:
    path = _chat_cache_path(key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data.get("response")


def _chat_cache_put(key: str, model: str, temperature: float, response: dict) -> None:
    config.CHAT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _chat_cache_path(key).write_text(
        json.dumps({"model": model, "temperature": temperature, "response": response}),
        encoding="utf-8",
    )


def chat(
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    temperature: float = 0,
    model: str | None = None,
) -> dict:
    """Returns the raw chat-completion response as a plain dict. Content-addressed cache
    (research.md R-09): a cache hit never calls the gateway."""
    model = model or config.chat_model()
    key = _chat_cache_key(model, temperature, messages, tools)

    cached = _chat_cache_get(key)
    if cached is not None:
        return cached

    try:
        client = _client()
        kwargs: dict = {"model": model, "messages": messages, "temperature": temperature}
        if tools:
            kwargs["tools"] = tools
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:
        raise UpstreamError(f"chat call to {model!r} failed: {exc}") from exc

    response_dict = response.model_dump()
    _chat_cache_put(key, model, temperature, response_dict)
    return response_dict
