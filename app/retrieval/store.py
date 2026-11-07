"""Repository layer: load the built index, cosine search, BM25 search (R-06)."""

from pathlib import Path

import numpy as np

from app import config
from app.retrieval import runbooks
from app.retrieval.bm25 import Bm25Index
from app.retrieval.bm25 import rare_tokens as _rare_tokens
from app.schemas import Chunk, IndexManifest


class StaleIndexError(Exception):
    """No index, or the loaded index predates the current corpus (FR-020)."""


class Store:
    def __init__(
        self,
        chunks: list[Chunk],
        manifest: IndexManifest,
        embeddings: np.ndarray | None,
        tcodes: dict[str, str],
    ):
        self.chunks = chunks
        self.manifest = manifest
        self.embeddings = embeddings
        self.tcodes = tcodes
        self.bm25 = Bm25Index(chunks)

    @classmethod
    def load(
        cls,
        index_dir: Path | None = None,
        runbook_dir: Path | None = None,
        tcodes_path: Path | None = None,
    ) -> "Store":
        index_dir = index_dir or config.INDEX_DIR
        manifest_path = index_dir / "manifest.json"
        chunks_path = index_dir / "chunks.jsonl"
        if not manifest_path.exists() or not chunks_path.exists():
            raise StaleIndexError(
                f"no index found at {index_dir}; run `python -m app.cli ingest`"
            )

        manifest = IndexManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))

        current_sha = runbooks.corpus_sha(runbook_dir, tcodes_path)
        if manifest.corpus_sha != current_sha:
            raise StaleIndexError(
                "index is stale: the corpus has changed since it was built; "
                "run `python -m app.cli ingest`"
            )

        lines = [l for l in chunks_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        chunks = [Chunk.model_validate_json(l) for l in lines]

        embeddings = None
        if manifest.n_vectors > 0:
            embeddings = np.load(index_dir / "embeddings.npy")
            if embeddings.shape[0] != len(chunks):
                raise StaleIndexError(
                    f"chunks.jsonl has {len(chunks)} lines but embeddings.npy has "
                    f"{embeddings.shape[0]} rows; re-run `python -m app.cli ingest`"
                )
            if embeddings.shape[1] != manifest.embed_dim:
                raise StaleIndexError(
                    f"embeddings.npy dim {embeddings.shape[1]} does not match manifest "
                    f"embed_dim {manifest.embed_dim}; re-run `python -m app.cli ingest`"
                )

        tcodes = runbooks.load_tcodes(tcodes_path)
        return cls(chunks, manifest, embeddings, tcodes)

    def bm25_search(self, query: str) -> list[tuple[Chunk, float]]:
        scores = self.bm25.scores(query)
        return list(zip(self.chunks, scores))

    def cosine_search(self, query_vector: np.ndarray) -> list[tuple[Chunk, float]]:
        if self.embeddings is None:
            raise StaleIndexError(
                "this index has no embeddings (built with --no-embed); "
                "re-run `python -m app.cli ingest` without --no-embed for dense/hybrid mode"
            )
        norm = np.linalg.norm(query_vector)
        normalised = query_vector / norm if norm else query_vector
        scores = self.embeddings @ normalised
        return list(zip(self.chunks, scores.tolist()))

    def rare_tokens(self, query: str) -> set[str]:
        return _rare_tokens(query, self.bm25.vocab, self.tcodes)
