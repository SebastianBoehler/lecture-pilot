from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from lecturepilot.coaching_contract import (
    MAX_APPROVED_TASK_LENGTH,
    AssessmentStage,
    AssistanceLevel,
    HintLevel,
)
from lecturepilot.scaffold_policy import TutorScaffoldPolicy


class UserMemoryContext(BaseModel):
    global_notes: str = Field(default="", max_length=4000)
    course_notes: str = Field(default="", max_length=4000)
    preferences: dict[str, Any] = Field(default_factory=dict)


class AgentConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8_000)


class AgentReadinessTask(BaseModel):
    id: str = Field(min_length=1, max_length=220)
    source_ref: str | None = Field(default=None, max_length=500)
    expected_evidence: str = Field(min_length=1, max_length=1000)
    scaffold_policy: TutorScaffoldPolicy


class AgentCoachingContext(BaseModel):
    active_gate_id: str | None = Field(default=None, max_length=160)
    active_gate_revision: str | None = Field(default=None, max_length=64)
    active_gate_review_after_days: int | None = Field(default=None, ge=1, le=365)
    session_goal: str = Field(default="", max_length=500)
    goal_is_new: bool = False
    prior_assistance: bool = False
    attendance_prior_used: bool = False
    needs_evidence_count: int = Field(default=0, ge=0)
    last_gate_status: Literal["passed", "needs_evidence"] | None = None
    delayed_transfer_due: bool = False
    support_before_attempt: bool = False
    last_assistance_level: AssistanceLevel = "none"
    pending_check_gate_id: str | None = Field(default=None, max_length=160)
    pending_check_gate_revision: str | None = Field(default=None, max_length=64)
    pending_check_kind: Literal["standard", "delayed_transfer"] | None = None
    pending_check_stage: AssessmentStage | None = None
    pending_check_issued_at: str | None = Field(default=None, max_length=80)
    pending_check_task_id: str | None = None
    exposed_task_ids: list[str] = Field(default_factory=list)
    pending_check_prompt: str | None = Field(default=None, max_length=MAX_APPROVED_TASK_LENGTH)
    pending_check_assistance_content: str | None = Field(default=None, max_length=2_000)
    exposed_hint_levels: list[HintLevel] = Field(default_factory=list, max_length=4)
    delayed_review_attempted: bool = False
    evidence_ids: list[str] = Field(default_factory=list, max_length=40)
    missing_evidence_ids: list[str] = Field(default_factory=list, max_length=40)
