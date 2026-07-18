from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class QualityGateStatus(StrEnum):
    PASSED = "passed"
    NEEDS_EVIDENCE = "needs_evidence"
    NOT_ASSESSED = "not_assessed"


class QualityGateDecision(BaseModel):
    gate_id: str = Field(min_length=1, max_length=120)
    status: QualityGateStatus
    reason: str = Field(min_length=1, max_length=500)
    next_prompt: str | None = Field(default=None, max_length=500)
    evidence_ids: list[str] = Field(default_factory=list, max_length=40)
    missing_evidence_ids: list[str] = Field(default_factory=list, max_length=40)
