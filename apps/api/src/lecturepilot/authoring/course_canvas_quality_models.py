from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CanvasQualityIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1, max_length=120)
    block_id: str | None = Field(default=None, max_length=120)
    reason: str = Field(min_length=1)
    # Objections to approved practice-* checkpoints are classified by the critic itself.
    decision: Literal["repair_section", "design_conflict", "dismiss"] = "repair_section"
    evidence_ids: list[str] = Field(default_factory=list, max_length=12)


class CanvasQualityPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issues: list[CanvasQualityIssue] = Field(max_length=30)
