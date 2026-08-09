from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    model_validator,
)

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

    @model_validator(mode="after")
    def validate_outcome(self) -> QuizOutcomeEvent:
        _validate_event_id(self)
        indices = [option.option_index for option in self.options]
        if indices != list(range(len(self.options))):
            raise ValueError("Quiz outcome options must have unique canonical indices.")
        option_ids = [option.option_id for option in self.options if option.option_id is not None]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("Quiz outcome option IDs must be unique.")
        selected = (
            self.options[self.option_index] if self.option_index < len(self.options) else None
        )
        if selected is None:
            raise ValueError("Quiz outcome selected option does not exist.")
        if self.option_id != selected.option_id:
            raise ValueError("Quiz outcome option ID does not match the selected option.")
        if self.correct_index is None:
            if self.correct is not None:
                raise ValueError("Unscored quiz outcomes cannot carry correctness.")
        else:
            if self.correct_index >= len(self.options):
                raise ValueError("Quiz outcome correct option does not exist.")
            if self.correct is not (self.option_index == self.correct_index):
                raise ValueError("Quiz outcome correctness does not match its option indices.")
        if self.attempt_index == 1 and self.first_attempt_correct is not self.correct:
            raise ValueError("First quiz attempt correctness is inconsistent.")
        expected = _correction_state(self.first_attempt_correct, self.correct)
        if self.correction_state != expected:
            raise ValueError("Quiz correction state is inconsistent with correctness.")
        return self


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

    @model_validator(mode="after")
    def validate_identity(self) -> GateOutcomeEvent:
        _validate_event_id(self)
        return self


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


def outcome_event_id(payload: BaseModel | dict) -> str:
    if isinstance(payload, BaseModel):
        data = payload.model_dump(mode="json")
    else:
        data = payload
    fields = _identity_fields(data.get("type"))
    identity = {field: data[field] for field in fields}
    encoded = json.dumps(
        identity,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def _identity_fields(event_type: object) -> tuple[str, ...]:
    shared = ("type", "course_id", "lecture_id", "user_key")
    if event_type == "quiz_answer":
        return shared + (
            "component_id",
            "publication_version",
            "learning_map_revision",
            "attempt_index",
        )
    if event_type == "gate_decision":
        return shared + (
            "gate_id",
            "gate_revision",
            "publication_version",
            "learning_map_revision",
            "attempt_kind",
            "attempt_index",
        )
    raise ValueError("Outcome analytics event type has no canonical identity.")


def _validate_event_id(event: BaseModel) -> None:
    if event.event_id != outcome_event_id(event):
        raise ValueError("Outcome analytics event ID does not match its canonical identity.")


def _correction_state(first_correct: bool | None, correct: bool | None) -> QuizCorrectionState:
    if correct is None:
        if first_correct is not None:
            raise ValueError("Unscored quiz outcome has scored first-attempt evidence.")
        return "not_needed"
    if first_correct is None:
        raise ValueError("Scored quiz outcome is missing first-attempt correctness.")
    if first_correct:
        if correct is not True:
            raise ValueError("A correct first attempt cannot become incorrect.")
        return "not_needed"
    return "corrected" if correct else "needed"
