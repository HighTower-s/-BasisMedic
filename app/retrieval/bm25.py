"""Tokenizer, BM25Okapi wrapper, and the rare-token gate signal (research.md R-03)."""

import re

from rank_bm25 import BM25Okapi

from app.schemas import Chunk

TOKEN_RE = re.compile(r"[A-Za-z0-9_/]+")
_RARE_SHAPE_RE = re.compile(r"^[A-Z][A-Z0-9_]{5,}$")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


class Bm25Index:
    """BM25Okapi over a fixed list of chunks, in chunk order."""

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        tokenized = [tokenize(c.text) for c in chunks]
        self._bm25 = BM25Okapi(tokenized) if tokenized else None
        self.vocab: set[str] = {tok for toks in tokenized for tok in toks}

    def scores(self, query: str) -> list[float]:
        if self._bm25 is None:
            return []
        return list(self._bm25.get_scores(tokenize(query)))


def rare_tokens(query: str, vocab: set[str], tcodes: dict[str, str]) -> set[str]:
    """A query token qualifies when it is in the corpus vocabulary AND is either
    shaped like an ABAP runtime error (research.md R-03) or a known T-code."""
    found = set()
    for token in TOKEN_RE.findall(query):
        if token.lower() not in vocab:
            continue
        if _RARE_SHAPE_RE.fullmatch(token) or token in tcodes:
            found.add(token)
    return found
