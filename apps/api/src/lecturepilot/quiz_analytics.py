from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel

from lecturepilot.analytics_outcomes import (
    AnalyticsOutcomeCell,
    AnalyticsVersionStatus,
    MIN_OUTCOME_CELL_SIZE,
    outcome_cell,
    version_sort_key,
    version_status,
)


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
    publication_version: int
    version_status: AnalyticsVersionStatus
    activity_events: int
    unique_learners: int
    first_attempt: AnalyticsOutcomeCell
    correction_after_feedback: AnalyticsOutcomeCell
    options: list[AnalyticsOptionMetric] | None


@dataclass
class _LearnerQuizState:
    first: dict
    first_index: int
    corrected: bool = False


@dataclass
class _QuizState:
    reference: dict
    publication_version: int
    activity_events: int = 0
    learners: dict[str, _LearnerQuizState] = field(default_factory=dict)


class QuizMetricsAccumulator:
    def __init__(self, *, current_publication_version: int) -> None:
        self.current_publication_version = current_publication_version
        self._groups: dict[tuple[str, int], _QuizState] = {}

    def record(self, event: dict) -> None:
        if event.get("type") != "quiz_answer":
            return
        publication_version = _publication_version(event)
        component_id = str(event["component_id"])
        key = component_id, publication_version
        state = self._groups.setdefault(
            key,
            _QuizState(reference=event, publication_version=publication_version),
        )
        state.activity_events += 1
        learner_key = str(event["user_key"])
        attempt_index = _attempt_index(event)
        learner = state.learners.get(learner_key)
        if learner is None:
            state.learners[learner_key] = _LearnerQuizState(
                first=event,
                first_index=attempt_index,
                corrected=event["correction_state"] == "corrected",
            )
        elif attempt_index < learner.first_index:
            learner.corrected = learner.corrected or learner.first.get("correct") is True
            learner.first = event
            learner.first_index = attempt_index
        elif attempt_index > learner.first_index and event["correct"] is True:
            learner.corrected = True

    def metrics(self) -> list[AnalyticsQuizMetric]:
        metrics = [self._metric(key[0], state) for key, state in self._groups.items()]
        return sorted(
            metrics,
            key=lambda item: (
                item.component_id,
                version_sort_key(item.publication_version, item.version_status),
            ),
        )

    def _metric(self, component_id: str, state: _QuizState) -> AnalyticsQuizMetric:
        reference = state.reference
        first_outcomes = {
            learner_key: learner.first.get("correct") is True
            for learner_key, learner in state.learners.items()
            if isinstance(learner.first.get("correct"), bool)
        }
        correction_outcomes = {
            learner_key: learner.corrected
            for learner_key, learner in state.learners.items()
            if learner.first.get("correct") is False
        }
        first_attempt = outcome_cell("quiz_first_attempt", first_outcomes)
        return AnalyticsQuizMetric(
            component_id=component_id,
            component_type=str(reference["component_type"]),
            title=str(reference["title"]),
            question=str(reference["question"]),
            publication_version=state.publication_version,
            version_status=version_status(
                state.publication_version,
                self.current_publication_version,
            ),
            activity_events=state.activity_events,
            unique_learners=len(state.learners),
            first_attempt=first_attempt,
            correction_after_feedback=outcome_cell(
                "correction_after_feedback", correction_outcomes
            ),
            options=_option_metrics(state) if first_attempt.data_status == "available" else None,
        )


def _option_metrics(state: _QuizState) -> list[AnalyticsOptionMetric] | None:
    reference = state.reference
    options = reference["options"]
    correct_index = reference["correct_index"]
    selections: dict[int, int] = {}
    for learner in state.learners.values():
        index = int(learner.first["option_index"])
        selections[index] = selections.get(index, 0) + 1
    if any(0 < count < MIN_OUTCOME_CELL_SIZE for count in selections.values()):
        return None
    metrics = []
    for option in options:
        index = int(option["option_index"])
        metrics.append(
            AnalyticsOptionMetric(
                option_index=index,
                option_id=option["option_id"],
                text=str(option["text"]),
                selections=selections.get(index, 0),
                correct=index == correct_index,
            )
        )
    return metrics


def _publication_version(event: dict) -> int:
    return int(event["publication_version"])


def _attempt_index(event: dict) -> int:
    return int(event["attempt_index"])
