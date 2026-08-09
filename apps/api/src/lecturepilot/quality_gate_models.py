from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class QualityGateStatus(StrEnum):
    PASSED = "passed"
    NEEDS_EVIDENCE = "needs_evidence"


class QualityGateDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    gate_id: str = Field(min_length=1, max_length=120)
    gate_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: QualityGateStatus
    reason: str = Field(min_length=1, max_length=500)
    evidence_ids: list[str] = Field(max_length=40)
    missing_evidence_ids: list[str] = Field(max_length=40)
