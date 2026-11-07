"""Build the search index atomically into data/index/ (R-04, FR-008, FR-009)."""

import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app import config
from app.retrieval import runbooks
from app.retrieval.chunk import chunk_by_section, chunk_fixed
from app.schemas import SECTION_ORDER, Chunk, ChunkStrategy, IndexManifest


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def _build_chunks(runbook_list: list, strategy: ChunkStrategy) -> list[Chunk]:
    if strategy == "section":
        return [chunk for rb in runbook_list for chunk in chunk_by_section(rb)]
    chunks: list[Chunk] = []
    for rb in runbook_list:
        full_text = "\n\n".join(rb.sections[name] for name in SECTION_ORDER)
        for i, window in enumerate(chunk_fixed(full_text)):
            chunks.append(
                Chunk(
                    chunk_id=f"{rb.doc_id}#f{i}",
                    doc_id=rb.doc_id,
                    category=rb.category,
                    section=None,
                    title=rb.title,
                    text=window,
                )
            )
    return chunks


def build_index(
    strategy: ChunkStrategy = "section",
    embed: bool = True,
    index_dir: Path | None = None,
) -> tuple[IndexManifest, int, int, int]:
    """Returns (manifest, n_tcodes, cache_hits, cache_misses). Atomic: a failure leaves
    the previous data/index/ untouched (R-04)."""
    index_dir = index_dir or config.INDEX_DIR
    tmp_dir = index_dir.parent / "index.tmp"

    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    try:
        runbook_list, tcodes = runbooks.load_corpus()
        chunks = _build_chunks(runbook_list, strategy)

        embed_model = None
        embed_dim = None
        n_vectors = 0
        cache_hits = cache_misses = 0

        if embed:
            from app import llm  # only module that calls the gateway (Constitution VI)

            texts = [c.text for c in chunks]
            vectors, cache_hits, cache_misses = llm.embed_with_cache_stats(texts)
            import numpy as np

            matrix = np.asarray(vectors, dtype=np.float32)
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            matrix = matrix / norms
            np.save(tmp_dir / "embeddings.npy", matrix)
            embed_model = config.embed_model()
            embed_dim = matrix.shape[1]
            n_vectors = matrix.shape[0]

        with (tmp_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(chunk.model_dump_json() + "\n")

        manifest = IndexManifest(
            corpus_sha=runbooks.corpus_sha(),
            chunk_strategy=strategy,
            embed_model=embed_model,
            embed_dim=embed_dim,
            n_runbooks=len(runbook_list),
            n_chunks=len(chunks),
            n_vectors=n_vectors,
            built_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            git_commit=_git_commit(),
        )
        (tmp_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

        if index_dir.exists():
            shutil.rmtree(index_dir)
        tmp_dir.rename(index_dir)
        return manifest, len(tcodes), cache_hits, cache_misses
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
