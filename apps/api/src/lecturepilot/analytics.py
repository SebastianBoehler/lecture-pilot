from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
import json
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.coaching_analytics import AnalyticsGateMetric, GateMetricsAccumulator
from lecturepilot.coaching_progress import CoachingTurnEvent
from lecturepilot.durable_files import exclusive_file_lock
from lecturepilot.learning_map import LearningMap
from lecturepilot.models import AttendanceStatus, QualityGateDecision
from lecturepilot.professor_preview import is_professor_preview_user_id
from lecturepilot.quiz_analytics import (
    AnalyticsOptionMetric as AnalyticsOptionMetric,
    AnalyticsQuizMetric as AnalyticsQuizMetric,
    QuizMetricsAccumulator,
)
from lecturepilot.storage_layout import StorageLayout, safe_id


class QuizAnswerInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attendance: AttendanceStatus
    block_id: str = Field(min_length=1, max_length=160)
    option_index: int = Field(ge=0, le=25)


class QuizAnswerResult(BaseModel):
    block_id: str
    component_id: str
    selected_index: int
    correct_index: int | None
    correct: bool | None


class LectureAnalyticsSummary(BaseModel):
    course_id: str
    lecture_id: str
    total_events: int
    unique_learners: int
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
    ) -> QuizAnswerResult:
        option_text = block.items[option_index] if option_index < len(block.items) else ""
        option_ids = block.option_ids or []
        option_id = option_ids[option_index] if option_index < len(option_ids) else None
        correct_index = block.answer_index if isinstance(block.answer_index, int) else None
        correct = option_index == correct_index if correct_index is not None else None
        component_id = block.component_id or block.id
        if not is_professor_preview_user_id(user_id):
            self._append(
                course_id,
                lecture_id,
                {
                    "type": "quiz_answer",
                    "course_id": course_id,
                    "lecture_id": lecture_id,
                    "user_key": self.layout.user_key(user_id),
                    "attendance": attendance.value,
                    "component_id": component_id,
                    "component_type": block.component_type or block.type,
                    "block_id": block.id,
                    "title": block.caption or "Retrieval check",
                    "question": block.text or "",
                    "option_index": option_index,
                    "option_id": option_id,
                    "option_text": option_text,
                    "correct_index": correct_index,
                    "correct": correct,
                    "options": _options_snapshot(block),
                    "created_at": _now(),
                },
            )
        return QuizAnswerResult(
            block_id=block.id,
            component_id=component_id,
            selected_index=option_index,
            correct_index=correct_index,
            correct=correct,
        )

    def record_quality_gate(
        self,
        *,
        course_id: str,
        lecture_id: str,
        user_id: str,
        attendance: AttendanceStatus,
        decision: QualityGateDecision,
        coaching_event: CoachingTurnEvent | None = None,
    ) -> None:
        if is_professor_preview_user_id(user_id):
            return
        learning_evidence = (
            coaching_event.model_dump(mode="json") if coaching_event is not None else {}
        )
        self._append(
            course_id,
            lecture_id,
            {
                "type": "gate_decision",
                "course_id": course_id,
                "lecture_id": lecture_id,
                "user_key": self.layout.user_key(user_id),
                "attendance": attendance.value,
                "gate_id": decision.gate_id,
                "status": decision.status.value,
                "reason": decision.reason,
                "assistance_level": learning_evidence.get("assistance_level", "unknown"),
                "support_before_attempt": learning_evidence.get("support_before_attempt", False),
                "independent_attempt": learning_evidence.get("independent_attempt", False),
                "transfer_attempt": learning_evidence.get("transfer_attempt", False),
                "support_profile": learning_evidence.get("support_profile"),
                "process_label": learning_evidence.get("process_label"),
                "evidence_ids": decision.evidence_ids,
                "created_at": _now(),
            },
        )

    def summary(self, *, course_id: str, lecture_id: str) -> LectureAnalyticsSummary:
        quizzes = QuizMetricsAccumulator()
        gates = GateMetricsAccumulator()
        learners: set[str] = set()
        total_events = 0
        for event in self.iter_events(course_id=course_id, lecture_id=lecture_id):
            total_events += 1
            if event.get("user_key"):
                learners.add(str(event["user_key"]))
            quizzes.record(event)
            gates.record(event)
        return LectureAnalyticsSummary(
            course_id=course_id,
            lecture_id=lecture_id,
            total_events=total_events,
            unique_learners=len(learners),
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
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    yield payload

    def _append(self, course_id: str, lecture_id: str, payload: dict) -> None:
        path = self._events_path(course_id, lecture_id)
        with exclusive_file_lock(path), path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _events_path(self, course_id: str, lecture_id: str) -> Path:
        return (
            self.layout.course_root(course_id)
            / "analytics"
            / "lectures"
            / safe_id(lecture_id)
            / "events.jsonl"
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
