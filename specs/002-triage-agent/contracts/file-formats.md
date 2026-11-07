# Contract: File Formats

**Feature**: `002-triage-agent`

Every new on-disk shape this feature reads or writes, extending Feature 1's
[file-formats.md](../../001-runbook-retrieval-eval/contracts/file-formats.md). Field-level rules live in
[data-model.md](../data-model.md); this document fixes the literal file layout.

Generated, git-ignored: `data/chat_cache/`. Committed: `eval/results/E4_*.json`, `eval/results/results.md`
(extended), `eval/results/failures.jsonl` (extended). Nothing Feature 1 committed changes shape.

---

## 1. `TriageResult` — returned by `triage()`, emitted by `--json`

```json
{
  "category": "memory_dump",
  "summary": "TSV_TNEW_PAGE_ALLOC_FAILED short dump during a background job; internal table exceeded memory",
  "tcodes": ["ST22", "ST02"],
  "unverified_tcodes": [],
  "steps": [
    {"action": "Open ST22 and read \"Error analysis\" for requested vs. used memory size.", "tcode": "ST22"},
    {"action": "Open ST02 and check extended/heap memory usage around the dump time.", "tcode": "ST02"}
  ],
  "escalate_to": "developer",
  "sources": ["mem_tsv_tnew_page_alloc#check", "mem_tsv_tnew_page_alloc#cause"],
  "confidence": "high"
}
```

Out-of-scope shape (FR-012 — `tcodes` and `sources` empty):

```json
{
  "category": "out_of_scope",
  "summary": "no runbook section cleared the relevance floor for this log",
  "tcodes": [],
  "unverified_tcodes": [],
  "steps": [{"action": "Not covered by the runbooks; investigate manually or escalate.", "tcode": null}],
  "escalate_to": null,
  "sources": [],
  "confidence": "low"
}
```

---

## 2. `data/chat_cache/<sha256>.json` — generated, git-ignored

One file per distinct `(model, temperature, messages, tools)` combination (R-09).

```json
{
  "model": "gemma-4-E4B-it",
  "temperature": 0,
  "key_includes": ["model", "temperature", "messages", "tools"],
  "response": { "...the raw chat-completion response, however the SDK returns it..." }
}
```

Content-addressed the same way as Feature 1's `data/cache/<sha256>.json` — a cache hit is byte-identical to the
original response.

---

## 3. `eval/results/E4_{config_slug}_{split}.json` — committed

One file per (experiment, configuration, split), same convention as Feature 1's R-11 — never overwritten by a
different configuration. Slug example: `E4_agent_test`.

```json
{
  "config": {
    "experiment": "E4", "name": "agent", "split": "test", "baseline": "agent",
    "max_steps": 5, "repair_attempts": 2, "chat_model": "gemma-4-E4B-it",
    "corpus_sha": "3f9a1c2e8b47…", "git_commit": "f06f1e5"
  },
  "aggregate": {
    "n_cases": 30,
    "category_accuracy": 0.0, "tcode_recall": 0.0,
    "unverified_claim_rate": 0.0, "valid_output_rate": 0.0,
    "by_difficulty": {"easy": {}, "medium": {}, "hard": {}, "thai": {}, "mixed": {}, "oos": {}}
  },
  "cases": [
    {
      "case_id": "t01", "gold_category": "memory_dump", "gold_tcodes": ["ST22", "ST02"],
      "produced": { "...the TriageResult shape from § 1..." },
      "steps_taken": 2, "repaired": false, "fell_back": false,
      "category_correct": true, "tcode_recall": 1.0, "unverified_claim": false
    }
  ]
}
```

Zeros above are placeholders showing shape — real files contain measured values only. `config` is machine-written;
`corpus_sha` and `git_commit` are copied from the loaded Feature-1 index manifest, never recomputed (mirrors
Feature 1's FR-035 discipline).

---

## 4. `eval/results/failures.jsonl` — committed, extended

Same file Feature 1 writes to, truncated at the start of each `eval/run_all.py` invocation (Feature 1's existing
behaviour, unchanged scope — this feature's records are appended in the same pass). New records use the
`FailureTypeE2E` values:

```json
{"case_id":"t12","config_name":"agent","expected_category":"user_auth","produced_category":"out_of_scope","expected_tcodes":["SU53","PFCG"],"produced_tcodes":[],"unverified_tcodes":[],"failure_type":"category_wrong","note":"hard case, no exact auth keyword — out_of_scope forced because the paraphrase didn't retrieve"}
```

---

## 5. `eval/results/results.md` — committed, generated, extended

Regenerated wholesale by `eval/run_all.py` (never hand-edited, same Feature-1 rule). New section appended after
Feature 1's existing content:

6. **E4 — end-to-end comparison** — full agent vs. `E-NoRAG` vs. `E-ClassicRAG`, test split, all four metrics,
   each row stating which baseline it is, a verdict sentence per metric stated plainly whether or not the agent
   wins (FR-022), and per-difficulty slices including Thai and mixed.
7. **Agent-specific limitations** appended to Feature 1's existing Limitations block: tool-calling reliability on
   a small model, the mixed-two-problem-log single-category constraint, and anything the chat cache's
   reproducibility guarantee does not cover (e.g. a gateway model version change between the first cache-writing
   run and a much later rerun).

Every new table header states which split and whether the metric is end-to-end (never conflated with Feature 1's
pre-gate/post-gate retrieval labelling).
