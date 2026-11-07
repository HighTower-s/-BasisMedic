from app.retrieval.bm25 import Bm25Index, rare_tokens, tokenize
from app.schemas import Chunk


def _chunk(doc_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=f"{doc_id}#symptoms",
        doc_id=doc_id,
        category="memory_dump",
        section="Symptoms",
        title=doc_id,
        text=text,
    )


def test_error_code_and_tcode_survive_as_whole_tokens():
    tokens = tokenize("Dump TSV_TNEW_PAGE_ALLOC_FAILED seen; check SM37 for the job.")
    assert "tsv_tnew_page_alloc_failed" in tokens
    assert "sm37" in tokens


def test_rc_equals_eight_splits_on_the_equals_sign():
    tokens = tokenize("Transport returned RC=8 during import.")
    assert "rc" in tokens
    assert "8" in tokens
    assert "rc=8" not in tokens


def test_thai_input_yields_zero_tokens():
    assert tokenize("งานถูกยกเลิกเพราะผู้ใช้ถูกล็อก") == []


def test_rare_tokens_in_corpus_error_code_qualifies():
    index = Bm25Index([_chunk("mem_alloc_fail", "TSV_TNEW_PAGE_ALLOC_FAILED seen here")])
    found = rare_tokens("Got TSV_TNEW_PAGE_ALLOC_FAILED today", index.vocab, tcodes={})
    assert found == {"TSV_TNEW_PAGE_ALLOC_FAILED"}


def test_rare_tokens_in_corpus_common_word_does_not_qualify():
    index = Bm25Index([_chunk("mem_alloc_fail", "the job was cancelled today")])
    found = rare_tokens("the job failed", index.vocab, tcodes={})
    assert found == set()


def test_rare_tokens_out_of_corpus_error_code_does_not_qualify():
    index = Bm25Index([_chunk("mem_alloc_fail", "something unrelated")])
    found = rare_tokens("Got TSV_TNEW_PAGE_ALLOC_FAILED today", index.vocab, tcodes={})
    assert found == set()


def test_rare_tokens_tcode_qualifies_via_allow_list():
    index = Bm25Index([_chunk("lock_old_entries", "check SM12 for stale locks")])
    found = rare_tokens("open SM12 now", index.vocab, tcodes={"SM12": "Lock Entries"})
    assert found == {"SM12"}
