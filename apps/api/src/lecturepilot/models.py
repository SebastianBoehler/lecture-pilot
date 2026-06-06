from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr

from lecturepilot.canvas_models import CanvasSection


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class QualityGateStatus(StrEnum):
    PASSED = "passed"
    NEEDS_EVIDENCE = "needs_evidence"
    NOT_ASSESSED = "not_assessed"


class ProviderCapability(StrEnum):
    CHAT = "chat"
    TOOL_CALLS = "tool_calls"
    STRUCTURED_JSON = "structured_json"
    LONG_CONTEXT = "long_context"


class TenantRole(StrEnum):
    TENANT_ADMIN = "tenant_admin"
    PROFESSOR = "professor"
    TUTOR = "tutor"
    STUDENT = "student"


class Tenant(BaseModel):
    id: str = Field(min_length=8, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    domain: str | None = Field(default=None, max_length=200)


class TenantMembership(BaseModel):
    tenant_id: str = Field(min_length=8, max_length=120)
    role: TenantRole


class UserProfile(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    username: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    display_name: str | None = Field(default=None, max_length=200)
    memberships: list[TenantMembership] = Field(default_factory=list)


class Course(BaseModel):
    id: str
    title: str
    professor: str
    term: str


class TuebingenLoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: SecretStr = Field(min_length=1, max_length=500)
    term: str = Field(default="Sommer 2026", min_length=1, max_length=80)


class TuebingenLoginResult(BaseModel):
    username: str
    email: str | None = None
    term: str
    courses: list[Course]


class Lecture(BaseModel):
    id: str
    course_id: str
    title: str
    date: date
    material_path: str | None = None


class LectureView(BaseModel):
    lecture: Lecture
    unlocked: bool
    attendance: AttendanceStatus = AttendanceStatus.UNKNOWN


class CanvasState(BaseModel):
    focused_section_id: str | None = None
    active_artifact_id: str | None = None


class AgentTurnInput(BaseModel):
    user_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    lecture_id: str = Field(min_length=1)
    attendance: AttendanceStatus
    message: str = Field(min_length=1, max_length=4000)
    canvas_state: CanvasState = Field(default_factory=CanvasState)


class CanvasCommand(BaseModel):
    type: Literal[
        "focus_section",
        "highlight_span",
        "open_artifact",
        "append_section",
        "update_section",
    ]
    section_id: str | None = None
    span_id: str | None = None
    highlight_text: str | None = Field(default=None, max_length=160)
    artifact_id: str | None = None
    section: CanvasSection | None = None


class ArtifactCommand(BaseModel):
    type: Literal["summary", "quiz", "code", "diagram"]
    title: str
    payload: dict[str, Any]


class QualityGateDecision(BaseModel):
    gate_id: str = Field(min_length=1, max_length=120)
    status: QualityGateStatus
    reason: str = Field(min_length=1, max_length=500)
    next_prompt: str | None = Field(default=None, max_length=500)


class AgentTurnResult(BaseModel):
    message: str
    canvas_commands: list[CanvasCommand] = Field(default_factory=list)
    artifacts: list[ArtifactCommand] = Field(default_factory=list)
    quality_gate: QualityGateDecision | None = None
    model: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProviderSettings(BaseModel):
    provider: str
    model: str
    api_key_env: str
    capabilities: set[ProviderCapability]
