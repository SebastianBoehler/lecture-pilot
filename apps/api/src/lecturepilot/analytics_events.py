from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from lecturepilot.learner_lesson_state_models import QuizCorrectionState
from lecturepilot.models import AttendanceStatus, QualityGateStatus


CanonicalId = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=160,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]
RevisionId = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]
EventId = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
NonEmptyText = Annotated[str, Field(strict=True, min_length=1)]


class AnalyticsOptionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    option_index: NonNegativeInt
    option_id: CanonicalId | None = None
    text: NonEmptyText


class QuizOutcomeEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    type: Literal["quiz_answer"] = "quiz_answer"
    event_id: EventId
    course_id: CanonicalId
    lecture_id: CanonicalId
    user_key: CanonicalId
    attendance: AttendanceStatus
    component_id: CanonicalId
    component_type: CanonicalId
    title: NonEmptyText
    question: NonEmptyText
    option_index: NonNegativeInt
    option_id: CanonicalId | None = None
    correct_index: NonNegativeInt | None = None
    correct: bool | None
    publication_version: PositiveInt
    learning_map_revision: RevisionId
    attempt_index: PositiveInt
    first_attempt_correct: bool | None
    correction_state: QuizCorrectionState
    options: list[AnalyticsOptionSnapshot]
    created_at: AwareDatetime


class GateOutcomeEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    type: Literal["gate_decision"] = "gate_decision"
    event_id: EventId
    course_id: CanonicalId
    lecture_id: CanonicalId
    user_key: CanonicalId
    attendance: AttendanceStatus
    gate_id: CanonicalId
    gate_revision: RevisionId
    publication_version: PositiveInt
    learning_map_revision: RevisionId
    status: QualityGateStatus
    attempt_kind: Literal["independent", "supported_retry", "delayed_transfer"]
    attempt_index: PositiveInt
    created_at: AwareDatetime


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
