"""Offline fixtures. No test in this suite may touch the network."""

import json

import numpy as np
import pytest

TCODES = {
    "ST22": "ABAP Dump Analysis - display and analyze ABAP runtime errors",
    "ST02": "Tune Summary - buffers, roll/paging, extended and heap memory",
    "SM37": "Job Overview - status, job log and details of background jobs",
    "SM12": "Lock Entries - display and delete SAP enqueue locks",
}

_RUNBOOK = """---
doc_id: {doc_id}
category: {category}
title: {title}
tcodes: [{tcodes}]
escalate_to: basis
references:
  - https://example.invalid/{doc_id}
---

## Symptoms
{symptom_text}

## Cause
Something in the system ran out of a resource it needed, which is the cause described here.

## Check
1. {first_tcode} - look at the detail that matters for this incident and note what it says.
2. SM37 - check whether a background job was involved in the failure.

## Fix
Reduce the demand first, then adjust configuration only after the analysis supports doing so.

## Escalate
Hand custom code to the developer and sizing questions to Basis, with the evidence attached.

## References
- Example reference page - https://example.invalid/{doc_id}
"""


def write_runbook(directory, doc_id, category, symptom_text, tcodes=("ST22", "ST02")):
    path = directory / f"{doc_id}.md"
    path.write_text(
        _RUNBOOK.format(
            doc_id=doc_id,
            category=category,
            title=f"{doc_id} test runbook title",
            tcodes=", ".join(tcodes),
            first_tcode=tcodes[0],
            symptom_text=symptom_text,
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def tcodes_file(tmp_path):
    path = tmp_path / "tcodes.json"
    path.write_text(json.dumps(TCODES), encoding="utf-8")
    return path


@pytest.fixture
def fake_corpus(tmp_path, tcodes_file):
    """Three runbooks with deliberately distinct rare tokens."""
    directory = tmp_path / "runbooks"
    directory.mkdir()
    write_runbook(
        directory,
        "mem_alloc_fail",
        "memory_dump",
        "The dump TSV_TNEW_PAGE_ALLOC_FAILED says no more storage space for an internal table.",
    )
    write_runbook(
        directory,
        "dialog_timeout",
        "timeout",
        "The dump TIME_OUT says the time limit was exceeded in a dialog work process.",
    )
    write_runbook(
        directory,
        "stale_lock",
        "lock_issue",
        "A document is locked by another user and SM12 shows an old lock entry for them.",
        tcodes=("SM12", "SM37"),
    )
    return directory, tcodes_file


@pytest.fixture
def mock_embed(monkeypatch):
    """Deterministic stand-in for app.llm.embed: hash-seeded unit vectors, 1024-dim."""
    calls: list[list[str]] = []

    def fake_embed(texts, model=None):
        calls.append(list(texts))
        out = []
        for text in texts:
            rng = np.random.default_rng(abs(hash(text)) % (2**32))
            vector = rng.standard_normal(1024).astype(np.float32)
            out.append(vector / np.linalg.norm(vector))
        return out

    import app.llm

    monkeypatch.setattr(app.llm, "embed", fake_embed)
    fake_embed.calls = calls  # type: ignore[attr-defined]
    return fake_embed
