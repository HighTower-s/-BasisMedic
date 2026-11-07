from app.retrieval.chunk import chunk_by_section, chunk_fixed
from app.retrieval.runbooks import parse_runbook


def test_chunk_fixed_short_input_returns_single_chunk():
    text = "short text"
    assert chunk_fixed(text, size=800, overlap=150) == [text]


def test_chunk_fixed_empty_input_returns_no_chunks():
    assert chunk_fixed("", size=800, overlap=150) == []


def test_chunk_fixed_window_boundaries():
    text = "x" * 2000
    windows = chunk_fixed(text, size=800, overlap=150)
    # step = 650; starts at 0, 650, 1300; last window must reach the end exactly once
    assert [len(w) for w in windows] == [800, 800, len(text) - 1300]
    assert windows[0] == text[0:800]
    assert windows[1] == text[650:1450]
    assert windows[-1] == text[1300:2000]
    assert windows[-1].endswith(text[-1])


def test_chunk_fixed_exact_multiple_has_no_trailing_duplicate_window():
    size, overlap = 800, 150
    step = size - overlap
    text = "y" * (step * 3 + size)  # ends exactly on a window boundary
    windows = chunk_fixed(text, size=size, overlap=overlap)
    assert windows[-1] == text[-size:]
    # no extra all-overlap trailing window once the last window reaches len(text)
    assert sum(len(w) for w in windows) >= len(text)


def test_chunk_by_section_yields_six_chunks_with_context_prefix(tmp_path, tcodes_file):
    from tests.conftest import write_runbook

    path = write_runbook(tmp_path, "mem_alloc_fail", "memory_dump", "The dump TSV_TNEW_PAGE_ALLOC_FAILED.")
    import json

    tcodes = json.loads(tcodes_file.read_text(encoding="utf-8"))
    runbook = parse_runbook(path, tcodes)

    chunks = chunk_by_section(runbook)

    assert len(chunks) == 6
    for chunk in chunks:
        assert chunk.chunk_id == f"mem_alloc_fail#{chunk.section.lower()}"
        assert chunk.doc_id == "mem_alloc_fail"
        prefix = f"[{runbook.title}] [{runbook.category}] {chunk.section}: "
        assert chunk.text.startswith(prefix)
