"""The only module that reads environment variables (Constitution V)."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNBOOK_DIR = ROOT / "data" / "runbooks"
TCODES_PATH = ROOT / "data" / "tcodes.json"
INDEX_DIR = ROOT / "data" / "index"
CACHE_DIR = ROOT / "data" / "cache"
CHAT_CACHE_DIR = ROOT / "data" / "chat_cache"


class ConfigError(Exception):
    """Required configuration is missing or malformed."""


def _str(name: str, default: str | None = None) -> str:
    value = os.environ.get(name) or default
    if not value:
        raise ConfigError(f"{name} is not set. Copy .env.example to .env and fill it in.")
    return value


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc


def _choice(name: str, default: str, allowed: tuple[str, ...]) -> str:
    value = _str(name, default)
    if value not in allowed:
        raise ConfigError(f"{name} must be one of {allowed}, got {value!r}")
    return value


# Only read when embeddings are actually needed, so bm25 mode works with no key at all.
def base_url() -> str:
    return _str("OPENAI_BASE_URL", "https://llm.nat-d.uk/v1")


def api_key() -> str:
    return _str("OPENAI_API_KEY")


def embed_model() -> str:
    return _str("EMBED_MODEL", "bge-m3")


def chat_model() -> str:
    return _str("CHAT_MODEL", "gemma-4-E4B-it")


def max_steps() -> int:
    return _int("MAX_STEPS", 5)


def retrieval_mode() -> str:
    return _choice("RETRIEVAL_MODE", "hybrid", ("dense", "bm25", "hybrid"))


def chunk_strategy() -> str:
    return _choice("CHUNK_STRATEGY", "section", ("fixed", "section"))


def top_k() -> int:
    return _int("TOP_K", 3)


def min_score() -> float:
    return _float("MIN_SCORE", 0.40)
