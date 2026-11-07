"""Pure chunking strategies. No I/O, no network (Constitution VI)."""

from app.schemas import SECTION_ORDER, Chunk, Runbook


def chunk_fixed(text: str, size: int = 800, overlap: int = 150) -> list[str]:
    """Naive sliding-window chunks, matching the course reference app's default."""
    if not text:
        return []
    if len(text) <= size:
        return [text]
    step = size - overlap
    windows = []
    start = 0
    while True:
        end = min(start + size, len(text))
        windows.append(text[start:end])
        if end == len(text):
            break
        start += step
    return windows


def chunk_by_section(runbook: Runbook) -> list[Chunk]:
    """One chunk per section, with a context prefix so an isolated chunk is still legible."""
    chunks = []
    for name in SECTION_ORDER:
        body = runbook.sections[name]
        prefix = f"[{runbook.title}] [{runbook.category}] {name}: "
        chunks.append(
            Chunk(
                chunk_id=f"{runbook.doc_id}#{name.lower()}",
                doc_id=runbook.doc_id,
                category=runbook.category,
                section=name,
                title=runbook.title,
                text=prefix + body,
            )
        )
    return chunks
