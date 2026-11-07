"""Labelled evaluation case schema and split-level invariants. See data-model.md 7-8."""

import json
import re
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from app import config
from app.retrieval.runbooks import load_tcodes
from app.schemas import Difficulty, EvalCategory, LogFormat, Split

CASES_DIR = config.ROOT / "eval"
_WORD_RE = re.compile(r"[a-z0-9]+")


class EvalCase(BaseModel):
    id: str = Field(pattern=r"^[dt]\d{2}$")
    split: Split
    format: LogFormat
    difficulty: Difficulty
    log: str = Field(min_length=10, max_length=4000)
    gold_category: EvalCategory
    gold_docs: list[str] = Field(default_factory=list)
    acceptable_docs: list[str] = Field(default_factory=list)
    gold_tcodes: list[str] = Field(default_factory=list)
    synthetic: bool = True
    notes: str = ""

    @field_validator("synthetic")
    @classmethod
    def _must_be_synthetic(cls, value: bool) -> bool:
        if not value:
            raise ValueError("every eval case log must be synthetic (FR-028)")
        return value

    @model_validator(mode="after")
    def _out_of_scope_shape(self) -> "EvalCase":
        is_oos = self.gold_category == "out_of_scope"
        if is_oos and (self.gold_docs or self.acceptable_docs or self.gold_tcodes):
            raise ValueError(f"{self.id}: out_of_scope case must have empty docs/tcodes")
        if not is_oos and not self.gold_docs:
            raise ValueError(f"{self.id}: in-scope case must have non-empty gold_docs")
        if set(self.gold_docs) & set(self.acceptable_docs):
            raise ValueError(f"{self.id}: gold_docs and acceptable_docs overlap")
        return self

    @property
    def is_in_scope(self) -> bool:
        return bool(self.gold_docs)

    @property
    def is_out_of_scope(self) -> bool:
        return self.gold_category == "out_of_scope"


def _words(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


class EvalSetError(Exception):
    """A split, or the pair of splits, violates a required invariant."""


def _shingles(words: list[str], n: int = 8) -> set[tuple[str, ...]]:
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def load_split(split: Split, path: Path | None = None) -> list[EvalCase]:
    path = path or (CASES_DIR / f"cases_{split}.jsonl")
    cases = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = EvalCase.model_validate_json(line)
        except Exception as exc:
            raise EvalSetError(f"{path}:{lineno}: {exc}") from exc
        if case.split != split:
            raise EvalSetError(f"{path}:{lineno}: case {case.id} has split={case.split!r}")
        cases.append(case)
    return cases


def validate_split(cases: list[EvalCase], split: Split, tcodes: dict[str, str], doc_ids: set[str]) -> None:
    ids = [c.id for c in cases]
    if len(set(ids)) != len(ids):
        raise EvalSetError(f"{split}: duplicate case ids")

    for case in cases:
        for doc in case.gold_docs + case.acceptable_docs:
            if doc not in doc_ids:
                raise EvalSetError(f"{case.id}: unknown runbook {doc!r}")
        for code in case.gold_tcodes:
            if code not in tcodes:
                raise EvalSetError(f"{case.id}: gold T-code {code!r} not in allow-list")

    if split == "dev":
        in_scope = [c for c in cases if c.is_in_scope]
        oos = [c for c in cases if c.is_out_of_scope]
        if len(cases) != 10 or len(in_scope) != 8 or len(oos) != 2:
            raise EvalSetError(f"dev split must be 8 in-scope + 2 out-of-scope, got {len(cases)}")
    else:
        in_scope = [c for c in cases if c.is_in_scope]
        oos = [c for c in cases if c.is_out_of_scope]
        mixed = [c for c in in_scope if len(c.gold_docs) >= 2]
        thai = [c for c in cases if c.format == "chat_thai"]
        if len(cases) != 30:
            raise EvalSetError(f"test split must have 30 cases, got {len(cases)}")
        if len(oos) != 4:
            raise EvalSetError(f"test split must have 4 out-of-scope cases, got {len(oos)}")
        if len(mixed) != 2:
            raise EvalSetError(f"test split must have 2 mixed cases, got {len(mixed)}")
        if len(in_scope) != 26:
            raise EvalSetError(f"test split must have 26 in-scope cases, got {len(in_scope)}")
        if len(thai) != 3 or any(c.difficulty != "hard" for c in thai):
            raise EvalSetError("test split must have exactly 3 hard chat_thai cases")

        single = [c for c in in_scope if len(c.gold_docs) == 1]
        from collections import Counter

        per_cat_diff = Counter((_category_of(c, doc_ids), c.difficulty) for c in single)
        from app.schemas import CATEGORIES

        for cat in CATEGORIES:
            for diff in ("easy", "medium", "hard"):
                if per_cat_diff[(cat, diff)] != 1:
                    raise EvalSetError(
                        f"test split needs exactly 1 {diff} case for {cat}, "
                        f"got {per_cat_diff[(cat, diff)]}"
                    )

        covered = {doc for c in cases for doc in c.gold_docs}
        missing = doc_ids - covered
        if missing:
            raise EvalSetError(f"runbooks never used as gold in test split: {sorted(missing)}")


def _category_of(case: EvalCase, doc_ids: set[str]) -> str:
    return case.gold_category


def check_no_copied_phrasing(
    cases: list[EvalCase],
    runbook_sections: dict[str, str],
    n: int = 8,
    excluded_sections: tuple[str, ...] = ("Symptoms",),
) -> None:
    """FR-029/SC-003: no case log shares a contiguous n-word span with any runbook's
    analysis prose (Cause/Check/Fix/Escalate/References).

    Symptoms is excluded by design, not by loophole: 09_eval_plan.md and
    runbook_TEMPLATE.md both require Symptoms to quote the literal SAP error text so
    BM25 can match it, and an "easy" case is defined by quoting that same official
    text. Flagging that intentional overlap would make the easy tier impossible to
    write. What FR-029 actually guards against is a case log lifting the runbook's
    own written Cause/Fix analysis, which is what inflates keyword retrieval
    unrealistically (09_eval_plan.md line 29) - and that is exactly what this still
    catches, since only Symptoms is excluded.
    """
    section_shingles: dict[str, set[tuple[str, ...]]] = {
        key: _shingles(_words(text), n)
        for key, text in runbook_sections.items()
        if not any(key.endswith(f"#{s}") for s in excluded_sections)
    }
    for case in cases:
        case_shingles = _shingles(_words(case.log), n)
        if not case_shingles:
            continue
        for key, shingles in section_shingles.items():
            overlap = case_shingles & shingles
            if overlap:
                raise EvalSetError(f"{case.id}: shares phrasing with {key}: {overlap}")


def check_no_cross_split_duplicates(dev: list[EvalCase], test: list[EvalCase]) -> None:
    def norm(text: str) -> str:
        return " ".join(_words(text))

    dev_norm = {norm(c.log) for c in dev}
    for case in test:
        if norm(case.log) in dev_norm:
            raise EvalSetError(f"{case.id}: log duplicated in dev split")
