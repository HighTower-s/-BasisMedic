"""Shared models and enumerations. See specs/001-runbook-retrieval-eval/data-model.md."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

Category = Literal[
    "memory_dump",
    "timeout",
    "job_failure",
    "lock_issue",
    "update_error",
    "transport_error",
    "user_auth",
    "rfc_error",
]
EvalCategory = Literal[
    "memory_dump",
    "timeout",
    "job_failure",
    "lock_issue",
    "update_error",
    "transport_error",
    "user_auth",
    "rfc_error",
    "out_of_scope",
]
SectionName = Literal["Symptoms", "Cause", "Check", "Fix", "Escalate", "References"]
EscalateTo = Literal["basis", "developer", "security", "dba", "network", "sap_support"]
ChunkStrategy = Literal["fixed", "section"]
RetrievalMode = Literal["dense", "bm25", "hybrid"]
Split = Literal["dev", "test"]
Difficulty = Literal["easy", "medium", "hard"]
LogFormat = Literal[
    "st22_header",
    "sm37_joblog",
    "sm21_syslog",
    "stms_log",
    "sm59_test",
    "user_email",
    "chat_thai",
    "hana_alert",
    "other",
]
FailureType = Literal["retrieval_miss", "gate_false_refusal", "gate_missed_oos", "partial_recall"]

# Feature 2 — triage agent
Confidence = Literal["high", "medium", "low"]
FailureTypeE2E = Literal[
    "category_wrong", "tcode_recall_miss", "unverified_claim",
    "repair_exhausted", "loop_exhausted", "schema_invalid_after_fallback",
]

SECTION_ORDER: tuple[SectionName, ...] = (
    "Symptoms",
    "Cause",
    "Check",
    "Fix",
    "Escalate",
    "References",
)
CATEGORIES: tuple[Category, ...] = (
    "memory_dump",
    "timeout",
    "job_failure",
    "lock_issue",
    "update_error",
    "transport_error",
    "user_auth",
    "rfc_error",
)

TCODE_RE = r"^[A-Z][A-Z0-9_/]{1,19}$"
DOC_ID_RE = r"^[a-z][a-z0-9_]{2,39}$"

# Query length bounds. Accept 10..4000 (docs/prepare/02_design.md 3.1, shared with
# Feature 2's TriageRequest); normalise the query down to 2000 (04_system_flow.md B2).
MIN_QUERY_CHARS = 10
MAX_QUERY_CHARS = 4000
MAX_NORMALISED_CHARS = 2000


class Runbook(BaseModel):
    doc_id: str = Field(pattern=DOC_ID_RE)
    category: Category
    title: str = Field(min_length=5, max_length=120)
    tcodes: list[str] = Field(min_length=1, max_length=8)
    escalate_to: EscalateTo
    references: list[HttpUrl] = Field(min_length=1)
    sections: dict[str, str]
    source_path: Path = Field(exclude=True)

    @field_validator("sections")
    @classmethod
    def _six_sections_in_order(cls, value: dict[str, str]) -> dict[str, str]:
        if tuple(value) != SECTION_ORDER:
            raise ValueError(
                f"sections must be exactly {SECTION_ORDER} in that order, got {tuple(value)}"
            )
        for name, body in value.items():
            if not 20 <= len(body) <= 1500:
                raise ValueError(f"section {name} is {len(body)} chars, must be 20-1500")
        return value


class Chunk(BaseModel):
    """One searchable unit. Its position in the chunk list is its embedding row."""

    chunk_id: str
    doc_id: str
    category: Category
    section: str | None
    title: str
    text: str


class Hit(BaseModel):
    chunk_id: str
    doc_id: str
    section: str | None
    text: str
    dense_score: float | None = None
    bm25_score: float | None = None
    fused_score: float | None = None
    rank: int = Field(ge=1)

    def score_for(self, mode: RetrievalMode) -> float:
        """The score this mode actually ranked by - never print an RRF score as a cosine."""
        if mode == "bm25":
            return self.bm25_score or 0.0
        if mode == "dense":
            return self.dense_score or 0.0
        return self.fused_score or 0.0


class IndexManifest(BaseModel):
    corpus_sha: str
    chunk_strategy: ChunkStrategy
    embed_model: str | None
    embed_dim: int | None
    n_runbooks: int
    n_chunks: int
    n_vectors: int
    built_at: str
    git_commit: str | None


class Step(BaseModel):
    """One checklist item in a TriageResult."""

    action: str = Field(min_length=5)
    tcode: str | None = None


class TriageResult(BaseModel):
    """The validated structured triage output. See specs/002-triage-agent/data-model.md § 2."""

    category: EvalCategory
    summary: str = Field(max_length=300)
    tcodes: list[str] = Field(max_length=6)
    unverified_tcodes: list[str] = Field(default_factory=list)
    steps: list[Step] = Field(min_length=1, max_length=8)
    escalate_to: EscalateTo | None = None
    sources: list[str] = Field(default_factory=list)
    confidence: Confidence

    @model_validator(mode="after")
    def _out_of_scope_shape(self) -> "TriageResult":
        if self.category == "out_of_scope" and (self.tcodes or self.sources):
            raise ValueError("out_of_scope result must have empty tcodes and sources (FR-012)")
        return self
