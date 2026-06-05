from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class ProviderCapability(StrEnum):
    CHAT = "chat"
    TOOL_CALLS = "tool_calls"
    STRUCTURED_JSON = "structured_json"
    LONG_CONTEXT = "long_context"


class Course(BaseModel):
    id: str
    title: str
    professor: str
    term: str


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
    type: Literal["focus_section", "highlight_span", "open_artifact"]
    section_id: str | None = None
    span_id: str | None = None
    artifact_id: str | None = None


class ArtifactCommand(BaseModel):
    type: Literal["summary", "quiz", "code", "diagram"]
    title: str
    payload: dict[str, Any]


class AgentTurnResult(BaseModel):
    message: str
    canvas_commands: list[CanvasCommand] = Field(default_factory=list)
    artifacts: list[ArtifactCommand] = Field(default_factory=list)
    model: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProviderSettings(BaseModel):
    provider: str
    model: str
    api_key_env: str
    capabilities: set[ProviderCapability]

