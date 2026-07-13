from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.learning_map import LearningMap
from lecturepilot.models import AttendanceStatus, QualityGateDecision
from lecturepilot.professor_preview import is_professor_preview_user_id
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


class AnalyticsOptionMetric(BaseModel):
    option_index: int
    option_id: str | None = None
    text: str
    selections: int
    correct: bool


class AnalyticsQuizMetric(BaseModel):
    component_id: str
    component_type: str
    title: str
    question: str
    total_attempts: int
    unique_learners: int
    correct_attempts: int
    correct_rate: float | None
    latest_activity: str | None
    attendance_split: dict[str, int]
    options: list[AnalyticsOptionMetric]


class AnalyticsGateMetric(BaseModel):
    gate_id: str
    total_events: int
    unique_learners: int
    latest_activity: str | None
    status_counts: dict[str, int]
    attendance_split: dict[str, int]


class LectureAnalyticsSummary(BaseModel):
    course_id: str
    lecture_id: str
    total_events: int
    learning_map: LearningMap | None = None
    quizzes: list[AnalyticsQuizMetric]
    gates: list[AnalyticsGateMetric]


@dataclass(frozen=True)
class _Event:
    payload: dict


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
    ) -> None:
        if is_professor_preview_user_id(user_id):
            return
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
                "created_at": _now(),
            },
        )

    def summary(self, *, course_id: str, lecture_id: str) -> LectureAnalyticsSummary:
        events = [event.payload for event in self._read(course_id, lecture_id)]
        return LectureAnalyticsSummary(
            course_id=course_id,
            lecture_id=lecture_id,
            total_events=len(events),
            quizzes=_quiz_metrics(events),
            gates=_gate_metrics(events),
        )

    def _append(self, course_id: str, lecture_id: str, payload: dict) -> None:
        path = self._events_path(course_id, lecture_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def _read(self, course_id: str, lecture_id: str) -> list[_Event]:
        path = self._events_path(course_id, lecture_id)
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                events.append(_Event(payload))
        return events

    def _events_path(self, course_id: str, lecture_id: str) -> Path:
        return (
            self.layout.course_root(course_id)
            / "analytics"
            / "lectures"
            / safe_id(lecture_id)
            / "events.jsonl"
        )


def _quiz_metrics(events: list[dict]) -> list[AnalyticsQuizMetric]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        if event.get("type") == "quiz_answer":
            grouped[str(event.get("component_id") or event.get("block_id"))].append(event)
    return [_quiz_metric(component_id, items) for component_id, items in sorted(grouped.items())]


def _quiz_metric(component_id: str, events: list[dict]) -> AnalyticsQuizMetric:
    latest = max(events, key=lambda item: str(item.get("created_at") or ""))
    correct_attempts = sum(1 for event in events if event.get("correct") is True)
    return AnalyticsQuizMetric(
        component_id=component_id,
        component_type=str(latest.get("component_type") or "quiz"),
        title=str(latest.get("title") or component_id),
        question=str(latest.get("question") or ""),
        total_attempts=len(events),
        unique_learners=len(
            {str(event.get("user_key")) for event in events if event.get("user_key")}
        ),
        correct_attempts=correct_attempts,
        correct_rate=round(correct_attempts / len(events), 4) if events else None,
        latest_activity=str(latest.get("created_at") or "") or None,
        attendance_split=_count_values(events, "attendance"),
        options=_option_metrics(events, latest),
    )


def _option_metrics(events: list[dict], latest: dict) -> list[AnalyticsOptionMetric]:
    selections = Counter(int(event.get("option_index", -1)) for event in events)
    options = latest.get("options") if isinstance(latest.get("options"), list) else []
    correct_index = latest.get("correct_index")
    metrics = []
    for option in options:
        if not isinstance(option, dict):
            continue
        index = int(option.get("option_index", -1))
        metrics.append(
            AnalyticsOptionMetric(
                option_index=index,
                option_id=option.get("option_id")
                if isinstance(option.get("option_id"), str)
                else None,
                text=str(option.get("text") or ""),
                selections=selections.get(index, 0),
                correct=index == correct_index,
            )
        )
    return metrics


def _gate_metrics(events: list[dict]) -> list[AnalyticsGateMetric]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        if event.get("type") == "gate_decision":
            grouped[str(event.get("gate_id") or "gate")].append(event)
    return [_gate_metric(gate_id, items) for gate_id, items in sorted(grouped.items())]


def _gate_metric(gate_id: str, events: list[dict]) -> AnalyticsGateMetric:
    latest = max(events, key=lambda item: str(item.get("created_at") or ""))
    return AnalyticsGateMetric(
        gate_id=gate_id,
        total_events=len(events),
        unique_learners=len(
            {str(event.get("user_key")) for event in events if event.get("user_key")}
        ),
        latest_activity=str(latest.get("created_at") or "") or None,
        status_counts=_count_values(events, "status"),
        attendance_split=_count_values(events, "attendance"),
    )


def _count_values(events: list[dict], key: Literal["attendance", "status"]) -> dict[str, int]:
    return dict(sorted(Counter(str(event.get(key) or "unknown") for event in events).items()))


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
