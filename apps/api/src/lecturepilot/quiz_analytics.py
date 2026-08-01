from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from pydantic import BaseModel


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


@dataclass
class _QuizState:
    latest: dict
    total_attempts: int = 0
    learners: set[str] = field(default_factory=set)
    correct_attempts: int = 0
    attendance: Counter[str] = field(default_factory=Counter)
    selections: Counter[int] = field(default_factory=Counter)


class QuizMetricsAccumulator:
    def __init__(self) -> None:
        self._groups: dict[str, _QuizState] = {}

    def record(self, event: dict) -> None:
        if event.get("type") != "quiz_answer":
            return
        component_id = str(event.get("component_id") or event.get("block_id"))
        state = self._groups.setdefault(component_id, _QuizState(latest=event))
        state.total_attempts += 1
        if event.get("user_key"):
            state.learners.add(str(event["user_key"]))
        state.correct_attempts += event.get("correct") is True
        state.attendance[str(event.get("attendance") or "unknown")] += 1
        state.selections[int(event.get("option_index", -1))] += 1
        if str(event.get("created_at") or "") >= str(state.latest.get("created_at") or ""):
            state.latest = event

    def metrics(self) -> list[AnalyticsQuizMetric]:
        return [
            self._metric(component_id, self._groups[component_id])
            for component_id in sorted(self._groups)
        ]

    def _metric(self, component_id: str, state: _QuizState) -> AnalyticsQuizMetric:
        latest = state.latest
        return AnalyticsQuizMetric(
            component_id=component_id,
            component_type=str(latest.get("component_type") or "quiz"),
            title=str(latest.get("title") or component_id),
            question=str(latest.get("question") or ""),
            total_attempts=state.total_attempts,
            unique_learners=len(state.learners),
            correct_attempts=state.correct_attempts,
            correct_rate=round(state.correct_attempts / state.total_attempts, 4),
            latest_activity=str(latest.get("created_at") or "") or None,
            attendance_split=dict(sorted(state.attendance.items())),
            options=_option_metrics(state),
        )


def _option_metrics(state: _QuizState) -> list[AnalyticsOptionMetric]:
    latest = state.latest
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
                selections=state.selections.get(index, 0),
                correct=index == correct_index,
            )
        )
    return metrics
