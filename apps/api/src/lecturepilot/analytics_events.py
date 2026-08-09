from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from lecturepilot.learner_lesson_state_models import QuizCorrectionState
from lecturepilot.models import AttendanceStatus, QualityGateStatus


class AnalyticsOptionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_index: int = Field(ge=0)
    option_id: str | None = None
    text: str


class QuizOutcomeEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["quiz_answer"] = "quiz_answer"
    course_id: str
    lecture_id: str
    user_key: str
    attendance: AttendanceStatus
    component_id: str
    component_type: str
    title: str
    question: str
    option_index: int = Field(ge=0)
    option_id: str | None = None
    correct_index: int | None = Field(default=None, ge=0)
    correct: bool | None
    publication_version: int = Field(ge=1)
    attempt_index: int = Field(ge=1)
    first_attempt_correct: bool | None
    correction_state: QuizCorrectionState
    options: list[AnalyticsOptionSnapshot]
    created_at: str


class GateOutcomeEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["gate_decision"] = "gate_decision"
    course_id: str
    lecture_id: str
    user_key: str
    attendance: AttendanceStatus
    gate_id: str
    gate_revision: str = Field(min_length=1, max_length=64)
    publication_version: int = Field(ge=1)
    learning_map_revision: str = Field(min_length=1, max_length=64)
    status: QualityGateStatus
    attempt_kind: Literal["independent", "supported_retry", "delayed_transfer"]
    attempt_index: int = Field(ge=1)
    created_at: str


AnalyticsOutcomeEvent = Annotated[
    QuizOutcomeEvent | GateOutcomeEvent,
    Field(discriminator="type"),
]
_EVENT_ADAPTER = TypeAdapter(AnalyticsOutcomeEvent)


class InvalidAnalyticsEventError(RuntimeError):
    pass


def parse_analytics_event(line: str) -> AnalyticsOutcomeEvent:
    try:
        return _EVENT_ADAPTER.validate_json(line)
    except ValidationError as exc:
        raise InvalidAnalyticsEventError(
            "Outcome analytics log contains an invalid event."
        ) from exc
