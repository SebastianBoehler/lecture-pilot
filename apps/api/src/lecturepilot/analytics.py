from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
import json
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.analytics_events import (
    GateOutcomeEvent,
    QuizOutcomeEvent,
    parse_analytics_event,
)
from lecturepilot.coaching_analytics import AnalyticsGateMetric, GateMetricsAccumulator
from lecturepilot.coaching_progress import CoachingTurnEvent
from lecturepilot.durable_files import exclusive_file_lock
from lecturepilot.learning_map import LearningMap
from lecturepilot.learner_lesson_state_models import QuizCorrectionState, QuizOutcome
from lecturepilot.models import AttendanceStatus, QualityGateDecision
from lecturepilot.professor_preview import is_professor_preview_user_id
from lecturepilot.quiz_identity import canonical_quiz_id
from lecturepilot.quiz_analytics import (
    AnalyticsOptionMetric as AnalyticsOptionMetric,
    AnalyticsQuizMetric as AnalyticsQuizMetric,
    QuizMetricsAccumulator,
)
from lecturepilot.storage_layout import StorageLayout, safe_id


class QuizAnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attendance: AttendanceStatus
    attempt_id: str = Field(min_length=8, max_length=160, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]+$")
    block_id: str = Field(min_length=1, max_length=160)
    option_index: int = Field(ge=0, le=25)


class QuizAnswerResult(BaseModel):
    block_id: str
    component_id: str
    selected_index: int
    correct: bool | None
    publication_version: int = Field(ge=1)
    attempt_index: int = Field(ge=1)
    first_attempt_correct: bool | None
    latest_outcome: QuizOutcome
    correction_state: QuizCorrectionState
    feedback: str = Field(min_length=1, max_length=500)


class LectureAnalyticsSummary(BaseModel):
    course_id: str
    lecture_id: str
    activity_events: int
    unique_learners: int
    current_publication_version: int
    current_learning_map_revision: str
    learning_map: LearningMap | None = None
    quizzes: list[AnalyticsQuizMetric]
    gates: list[AnalyticsGateMetric]


class AnalyticsStore:
    def __init__(self, layout: StorageLayout) -> None:
        self.layout = layout

    def record_quiz_answer(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
        attendance: AttendanceStatus,
        block: CanvasBlock,
        option_index: int,
        publication_version: int,
        attempt_index: int,
        first_attempt_correct: bool | None = None,
        correction_state: QuizCorrectionState = "not_needed",
    ) -> None:
        option_ids = block.option_ids or []
        option_id = option_ids[option_index] if option_index < len(option_ids) else None
        correct_index = block.answer_index if isinstance(block.answer_index, int) else None
        correct = option_index == correct_index if correct_index is not None else None
        component_id = canonical_quiz_id(block)
        if not is_professor_preview_user_id(user_id):
            self._append(
                course_id,
                lecture_id,
                QuizOutcomeEvent(
                    course_id=course_id,
                    lecture_id=lecture_id,
                    user_key=self.layout.user_key(user_id),
                    attendance=attendance,
                    component_id=component_id,
                    component_type=block.component_type or block.type,
                    title=block.caption or "Retrieval check",
                    question=block.text or "",
                    option_index=option_index,
                    option_id=option_id,
                    correct_index=correct_index,
                    correct=correct,
                    publication_version=publication_version,
                    attempt_index=attempt_index,
                    first_attempt_correct=first_attempt_correct,
                    correction_state=correction_state,
                    options=_options_snapshot(block),
                    created_at=_now(),
                ),
            )

    def record_quality_gate(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
        attendance: AttendanceStatus,
        decision: QualityGateDecision,
        publication_version: int,
        learning_map_revision: str,
        coaching_event: CoachingTurnEvent,
    ) -> None:
        if is_professor_preview_user_id(user_id):
            return
        if coaching_event.gate_id != decision.gate_id:
            raise ValueError("Gate analytics event does not match the quality-gate decision.")
        if (
            not coaching_event.gate_revision
            or coaching_event.attempt_kind == "none"
            or coaching_event.attempt_index is None
        ):
            raise ValueError("Gate analytics requires a versioned assessed attempt.")
        self._append(
            course_id,
            lecture_id,
            GateOutcomeEvent(
                course_id=course_id,
                lecture_id=lecture_id,
                user_key=self.layout.user_key(user_id),
                attendance=attendance,
                gate_id=decision.gate_id,
                gate_revision=coaching_event.gate_revision,
                publication_version=publication_version,
                learning_map_revision=learning_map_revision,
                status=decision.status,
                attempt_kind=coaching_event.attempt_kind,
                attempt_index=coaching_event.attempt_index,
                created_at=_now(),
            ),
        )

    def summary(
        self,
        *,
        course_id: str,
        lecture_id: str,
        current_publication_version: int,
        current_gate_revisions: dict[str, str],
        current_learning_map_revision: str,
    ) -> LectureAnalyticsSummary:
        quizzes = QuizMetricsAccumulator(current_publication_version=current_publication_version)
        gates = GateMetricsAccumulator(
            current_publication_version=current_publication_version,
            current_gate_revisions=current_gate_revisions,
        )
        learners: set[str] = set()
        activity_events = 0
        for event in self.iter_events(course_id=course_id, lecture_id=lecture_id):
            activity_events += 1
            if event.get("user_key"):
                learners.add(str(event["user_key"]))
            quizzes.record(event)
            gates.record(event)
        return LectureAnalyticsSummary(
            course_id=course_id,
            lecture_id=lecture_id,
            activity_events=activity_events,
            unique_learners=len(learners),
            current_publication_version=current_publication_version,
            current_learning_map_revision=current_learning_map_revision,
            quizzes=quizzes.metrics(),
            gates=gates.metrics(),
        )

    def events(self, *, course_id: str, lecture_id: str) -> list[dict]:
        return list(self.iter_events(course_id=course_id, lecture_id=lecture_id))

    def iter_events(self, *, course_id: str, lecture_id: str) -> Iterator[dict]:
        path = self._events_path(course_id, lecture_id)
        if not path.exists():
            return
        with exclusive_file_lock(path), path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                yield parse_analytics_event(line).model_dump(mode="json")

    def _append(
        self, course_id: str, lecture_id: str, payload: QuizOutcomeEvent | GateOutcomeEvent
    ) -> None:
        path = self._events_path(course_id, lecture_id)
        with exclusive_file_lock(path), path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload.model_dump(mode="json"), sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _events_path(self, course_id: str, lecture_id: str) -> Path:
        return (
            self.layout.course_root(course_id)
            / "analytics"
            / "lectures"
            / safe_id(lecture_id)
            / "outcome-events.jsonl"
        )


def _options_snapshot(block: CanvasBlock) -> list[dict]:
    return [
        {
            "option_index": index,
            "option_id": block.option_ids[index] if index < len(block.option_ids or []) else None,
            "text": text,
        }
        for index, text in enumerate(block.items)
    ]


def _now() -> str:
    return datetime.now(UTC).isoformat()
