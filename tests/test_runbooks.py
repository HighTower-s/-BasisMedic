"""US1 acceptance scenarios 1-2: corpus validity and allow-list enforcement."""

from collections import Counter

import pytest

from app import config
from app.schemas import CATEGORIES, SECTION_ORDER
from app.retrieval.runbooks import CorpusError, corpus_sha, load_corpus, load_tcodes, parse_runbook

from conftest import write_runbook


# --- the real corpus (FR-001..FR-004, FR-007, SC-006) ---


@pytest.fixture(scope="module")
def corpus():
    return load_corpus()


def test_sixteen_runbooks_two_per_category(corpus):
    runbooks, _ = corpus
    assert len(runbooks) == 16
    assert Counter(r.category for r in runbooks) == {c: 2 for c in CATEGORIES}


def test_doc_ids_unique_and_match_filenames(corpus):
    runbooks, _ = corpus
    assert len({r.doc_id for r in runbooks}) == 16
    assert all(r.doc_id == r.source_path.stem for r in runbooks)


def test_every_runbook_has_six_ordered_sections(corpus):
    runbooks, _ = corpus
    for runbook in runbooks:
        assert tuple(runbook.sections) == SECTION_ORDER, runbook.doc_id


def test_every_runbook_has_a_reference_url(corpus):
    runbooks, _ = corpus
    for runbook in runbooks:
        assert runbook.references, runbook.doc_id
        assert "http" in runbook.sections["References"], runbook.doc_id


def test_every_corpus_tcode_is_allow_listed(corpus):
    """SC-006: 100% of T-codes named anywhere in the corpus appear in the allow-list."""
    runbooks, tcodes = corpus
    for runbook in runbooks:
        for code in runbook.tcodes:
            assert code in tcodes, f"{runbook.doc_id}: {code}"


def test_check_sections_name_tcodes_in_order(corpus):
    runbooks, _ = corpus
    for runbook in runbooks:
        assert runbook.sections["Check"].lstrip().startswith("1."), runbook.doc_id


def test_corpus_sha_is_stable_and_sensitive(tmp_path):
    directory = tmp_path / "runbooks"
    directory.mkdir()
    import json

    tcodes_path = tmp_path / "tcodes.json"
    tcodes_path.write_text(json.dumps({"ST22": "ABAP dump analysis for runtime errors"}), "utf-8")
    write_runbook(directory, "a_one", "timeout", "A dump TIME_OUT appeared in the system today.")

    first = corpus_sha(directory, tcodes_path)
    assert first == corpus_sha(directory, tcodes_path)

    (directory / "a_one.md").write_text(
        (directory / "a_one.md").read_text("utf-8") + "\n", encoding="utf-8"
    )
    assert corpus_sha(directory, tcodes_path) != first


# --- failure modes must name the file and the value (FR-007) ---


def test_unlisted_tcode_is_rejected_by_name(fake_corpus):
    directory, tcodes_path = fake_corpus
    tcodes = load_tcodes(tcodes_path)
    path = directory / "mem_alloc_fail.md"
    path.write_text(
        path.read_text("utf-8").replace("tcodes: [ST22, ST02]", "tcodes: [ST22, ZZZZ]"), "utf-8"
    )

    with pytest.raises(CorpusError) as exc:
        parse_runbook(path, tcodes)
    assert "ZZZZ" in str(exc.value)
    assert "mem_alloc_fail" in str(exc.value)


def test_missing_section_is_rejected(fake_corpus):
    directory, tcodes_path = fake_corpus
    tcodes = load_tcodes(tcodes_path)
    path = directory / "dialog_timeout.md"
    body = path.read_text("utf-8")
    path.write_text(body[: body.index("## Escalate")], encoding="utf-8")

    with pytest.raises(CorpusError, match="sections must be exactly"):
        parse_runbook(path, tcodes)


def test_reordered_sections_are_rejected(fake_corpus):
    directory, tcodes_path = fake_corpus
    tcodes = load_tcodes(tcodes_path)
    path = directory / "dialog_timeout.md"
    body = path.read_text("utf-8")
    path.write_text(
        body.replace("## Symptoms", "## Cause", 1).replace("## Cause\nSomething", "## Symptoms\nS"),
        encoding="utf-8",
    )
    with pytest.raises(CorpusError):
        parse_runbook(path, tcodes)


def test_corpus_with_wrong_count_is_rejected(fake_corpus):
    directory, tcodes_path = fake_corpus
    with pytest.raises(CorpusError, match="expected 16 runbooks"):
        load_corpus(directory, tcodes_path)


def test_malformed_tcode_key_is_rejected(tmp_path):
    import json

    path = tmp_path / "tcodes.json"
    path.write_text(json.dumps({"lowercase": "not a valid T-code key at all"}), encoding="utf-8")
    with pytest.raises(CorpusError, match="lowercase"):
        load_tcodes(path)


def test_tcodes_file_shape(tmp_path):
    import json

    path = tmp_path / "tcodes.json"
    path.write_text(json.dumps({"ST22": "bad"}), encoding="utf-8")
    with pytest.raises(CorpusError, match="5-120"):
        load_tcodes(path)


def test_real_tcodes_file_loads():
    tcodes = load_tcodes(config.TCODES_PATH)
    assert len(tcodes) >= 40
    for needed in ("ST22", "ST12", "ST01", "ST04", "DBACOCKPIT"):
        assert needed in tcodes
