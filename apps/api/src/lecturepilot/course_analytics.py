from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel


class CourseLectureAnalytics(BaseModel):
    lecture_id: str
    total_events: int
    unique_learners: int
    quiz_attempts: int
    quiz_correct_attempts: int
    quiz_rate: float | None
    gate_checks: int
    gate_passes: int
    gate_rate: float | None


class CourseAnalyticsSummary(BaseModel):
    course_id: str
    total_events: int
    unique_learners: int
    quiz_attempts: int
    quiz_correct_attempts: int
    quiz_rate: float | None
    gate_checks: int
    gate_passes: int
    gate_rate: float | None
    lectures: list[CourseLectureAnalytics]


def course_analytics_summary(
    *,
    course_id: str,
    lecture_ids: list[str],
    read_events: Callable[[str], list[dict]],
) -> CourseAnalyticsSummary:
    course_learners: set[str] = set()
    lectures: list[CourseLectureAnalytics] = []
    for lecture_id in lecture_ids:
        events = read_events(lecture_id)
        course_learners.update(_learner_keys(events))
        lectures.append(_lecture_summary(lecture_id, events))

    quiz_attempts = sum(item.quiz_attempts for item in lectures)
    quiz_correct = sum(item.quiz_correct_attempts for item in lectures)
    gate_checks = sum(item.gate_checks for item in lectures)
    gate_passes = sum(item.gate_passes for item in lectures)
    return CourseAnalyticsSummary(
        course_id=course_id,
        total_events=sum(item.total_events for item in lectures),
        unique_learners=len(course_learners),
        quiz_attempts=quiz_attempts,
        quiz_correct_attempts=quiz_correct,
        quiz_rate=_rate(quiz_correct, quiz_attempts),
        gate_checks=gate_checks,
        gate_passes=gate_passes,
        gate_rate=_rate(gate_passes, gate_checks),
        lectures=lectures,
    )


def _lecture_summary(lecture_id: str, events: list[dict]) -> CourseLectureAnalytics:
    quiz_events = [event for event in events if event.get("type") == "quiz_answer"]
    gate_events = [event for event in events if event.get("type") == "gate_decision"]
    quiz_correct = sum(event.get("correct") is True for event in quiz_events)
    gate_passes = sum(event.get("status") == "passed" for event in gate_events)
    return CourseLectureAnalytics(
        lecture_id=lecture_id,
        total_events=len(events),
        unique_learners=len(_learner_keys(events)),
        quiz_attempts=len(quiz_events),
        quiz_correct_attempts=quiz_correct,
        quiz_rate=_rate(quiz_correct, len(quiz_events)),
        gate_checks=len(gate_events),
        gate_passes=gate_passes,
        gate_rate=_rate(gate_passes, len(gate_events)),
    )


def _learner_keys(events: list[dict]) -> set[str]:
    return {str(event["user_key"]) for event in events if event.get("user_key")}


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None
