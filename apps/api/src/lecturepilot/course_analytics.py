from __future__ import annotations

from collections.abc import Callable, Iterable

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
    read_events: Callable[[str], Iterable[dict]],
) -> CourseAnalyticsSummary:
    course_learners: set[str] = set()
    lectures: list[CourseLectureAnalytics] = []
    for lecture_id in lecture_ids:
        lecture, learners = _lecture_summary(lecture_id, read_events(lecture_id))
        course_learners.update(learners)
        lectures.append(lecture)

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


def _lecture_summary(
    lecture_id: str, events: Iterable[dict]
) -> tuple[CourseLectureAnalytics, set[str]]:
    total_events = 0
    learners: set[str] = set()
    quiz_attempts = 0
    quiz_correct = 0
    gate_checks = 0
    gate_passes = 0
    for event in events:
        total_events += 1
        if event.get("user_key"):
            learners.add(str(event["user_key"]))
        if event.get("type") == "quiz_answer":
            quiz_attempts += 1
            quiz_correct += event.get("correct") is True
        elif event.get("type") == "gate_decision":
            gate_checks += 1
            gate_passes += event.get("status") == "passed"
    summary = CourseLectureAnalytics(
        lecture_id=lecture_id,
        total_events=total_events,
        unique_learners=len(learners),
        quiz_attempts=quiz_attempts,
        quiz_correct_attempts=quiz_correct,
        quiz_rate=_rate(quiz_correct, quiz_attempts),
        gate_checks=gate_checks,
        gate_passes=gate_passes,
        gate_rate=_rate(gate_passes, gate_checks),
    )
    return summary, learners


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None
