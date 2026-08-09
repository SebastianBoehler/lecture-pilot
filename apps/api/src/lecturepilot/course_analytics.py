from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from pydantic import BaseModel

from lecturepilot.analytics_outcomes import (
    AnalyticsOutcomeCell,
    MIN_OUTCOME_CELL_SIZE,
)

_EVIDENCE_TYPES = (
    "quiz_first_attempt",
    "correction_after_feedback",
    "independent_first_pass",
    "supported_retry",
    "delayed_transfer",
)


@dataclass(frozen=True)
class CurrentLectureAnalyticsContract:
    publication_version: int
    learning_map_revision: str
    gate_revisions: dict[str, str]


class CourseLectureAnalytics(BaseModel):
    lecture_id: str
    activity_events: int
    unique_learners: int
    current_publication_version: int
    current_learning_map_revision: str
    quiz_first_attempt: AnalyticsOutcomeCell
    correction_after_feedback: AnalyticsOutcomeCell
    independent_first_pass: AnalyticsOutcomeCell
    supported_retry: AnalyticsOutcomeCell
    delayed_transfer: AnalyticsOutcomeCell


class CourseAnalyticsSummary(BaseModel):
    course_id: str
    activity_events: int
    unique_learners: int
    quiz_first_attempt: AnalyticsOutcomeCell
    correction_after_feedback: AnalyticsOutcomeCell
    independent_first_pass: AnalyticsOutcomeCell
    supported_retry: AnalyticsOutcomeCell
    delayed_transfer: AnalyticsOutcomeCell
    lectures: list[CourseLectureAnalytics]


@dataclass
class _Attempt:
    index: int
    passed: bool


@dataclass
class _QuizAttempt:
    index: int
    correct: bool
    corrected: bool = False


@dataclass
class _Aggregate:
    activity_events: int = 0
    learners: set[str] = field(default_factory=set)
    quiz: dict[str, dict[str, _QuizAttempt]] = field(default_factory=dict)
    attempts: dict[str, dict[str, dict[str, _Attempt]]] = field(
        default_factory=lambda: {kind: {} for kind in _EVIDENCE_TYPES[2:]}
    )

    def record(
        self, lecture_id: str, event: dict, contract: CurrentLectureAnalyticsContract
    ) -> None:
        self.activity_events += 1
        user_key = event["user_key"]
        self.learners.add(user_key)
        if (
            event["publication_version"] != contract.publication_version
            or event["learning_map_revision"] != contract.learning_map_revision
        ):
            return
        if event["type"] == "quiz_answer":
            self._record_quiz(lecture_id, user_key, event)
        elif event["type"] == "gate_decision":
            self._record_gate(lecture_id, user_key, event, contract)

    def cells(self) -> dict[str, AnalyticsOutcomeCell]:
        quiz_first = {
            learner: {item: attempt.correct for item, attempt in items.items()}
            for learner, items in self.quiz.items()
        }
        corrections = {
            learner: {
                item: attempt.corrected for item, attempt in items.items() if not attempt.correct
            }
            for learner, items in self.quiz.items()
        }
        return {
            "quiz_first_attempt": _score_cell("quiz_first_attempt", quiz_first),
            "correction_after_feedback": _score_cell("correction_after_feedback", corrections),
            **{
                kind: _score_cell(
                    kind,
                    {
                        learner: {item: attempt.passed for item, attempt in items.items()}
                        for learner, items in self.attempts[kind].items()
                    },
                )
                for kind in _EVIDENCE_TYPES[2:]
            },
        }

    def _record_quiz(self, lecture_id: str, learner: str, event: dict) -> None:
        correct = event["correct"]
        index = event["attempt_index"]
        if correct is None:
            return
        item = f"{lecture_id}:{event['component_id']}"
        attempts = self.quiz.setdefault(learner, {})
        current = attempts.get(item)
        if current is None or index < current.index:
            attempts[item] = _QuizAttempt(
                index=index,
                correct=correct,
                corrected=(current.corrected or current.correct) if current else False,
            )
        elif index > current.index and correct:
            current.corrected = True

    def _record_gate(
        self,
        lecture_id: str,
        learner: str,
        event: dict,
        contract: CurrentLectureAnalyticsContract,
    ) -> None:
        gate_id = event["gate_id"]
        if event["gate_revision"] != contract.gate_revisions.get(gate_id):
            return
        kind = event["attempt_kind"]
        evidence_type = {
            "independent": "independent_first_pass",
            "supported_retry": "supported_retry",
            "delayed_transfer": "delayed_transfer",
        }[kind]
        index = event["attempt_index"]
        if evidence_type == "independent_first_pass" and index != 1:
            return
        item = f"{lecture_id}:{gate_id}"
        attempts = self.attempts[evidence_type].setdefault(learner, {})
        current = attempts.get(item)
        if current is None or index < current.index:
            attempts[item] = _Attempt(index=index, passed=event["status"] == "passed")


def course_analytics_summary(
    *,
    course_id: str,
    lecture_ids: list[str],
    read_events: Callable[[str], Iterable[dict]],
    current_contracts: dict[str, CurrentLectureAnalyticsContract],
) -> CourseAnalyticsSummary:
    course = _Aggregate()
    lectures: list[CourseLectureAnalytics] = []
    for lecture_id in lecture_ids:
        contract = current_contracts[lecture_id]
        lecture = _Aggregate()
        for event in read_events(lecture_id):
            lecture.record(lecture_id, event, contract)
            course.record(lecture_id, event, contract)
        lectures.append(
            CourseLectureAnalytics(
                lecture_id=lecture_id,
                activity_events=lecture.activity_events,
                unique_learners=len(lecture.learners),
                current_publication_version=contract.publication_version,
                current_learning_map_revision=contract.learning_map_revision,
                **lecture.cells(),
            )
        )
    return CourseAnalyticsSummary(
        course_id=course_id,
        activity_events=course.activity_events,
        unique_learners=len(course.learners),
        lectures=lectures,
        **course.cells(),
    )


def lecture_outcome_cells(
    *,
    lecture_id: str,
    events: Iterable[dict],
    current_contract: CurrentLectureAnalyticsContract,
) -> dict[str, AnalyticsOutcomeCell]:
    aggregate = _Aggregate()
    for event in events:
        aggregate.record(lecture_id, event, current_contract)
    return aggregate.cells()


def _score_cell(evidence_type: str, scores: dict[str, dict[str, bool]]) -> AnalyticsOutcomeCell:
    learner_scores = [sum(items.values()) / len(items) for items in scores.values() if items]
    available = len(learner_scores) >= MIN_OUTCOME_CELL_SIZE
    return AnalyticsOutcomeCell(
        evidence_type=evidence_type,
        sample_size=len(learner_scores),
        data_status="available" if available else "insufficient_data",
        rate=(round(sum(learner_scores) / len(learner_scores), 4) if available else None),
    )
