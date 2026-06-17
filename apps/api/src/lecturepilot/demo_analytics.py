from __future__ import annotations

import re

from lecturepilot.analytics import (
    AnalyticsGateMetric,
    AnalyticsOptionMetric,
    AnalyticsQuizMetric,
    LectureAnalyticsSummary,
)

DEMO_ANALYTICS_COURSES = {"martius-ml", "demo-ml-course"}


def demo_lecture_analytics(course_id: str, lecture_id: str) -> LectureAnalyticsSummary | None:
    if course_id not in DEMO_ANALYTICS_COURSES:
        return None
    seed = _lecture_seed(lecture_id)
    attempts = 18 + seed * 3
    correct = max(1, int(attempts * (0.48 + (seed % 5) * 0.07)))
    learners = 8 + seed
    gate_checks = 9 + seed * 2
    passed = max(1, int(gate_checks * (0.55 + (seed % 4) * 0.06)))
    quiz = AnalyticsQuizMetric(
        component_id=f"lecture-{seed:02d}-retrieval",
        component_type="single_choice_quiz",
        title="Core concept retrieval",
        question="Which answer best captures the lecture's decision concept?",
        total_attempts=attempts,
        unique_learners=learners,
        correct_attempts=correct,
        correct_rate=round(correct / attempts, 4),
        latest_activity=None,
        attendance_split={"absent": max(1, learners // 3), "present": learners - max(1, learners // 3)},
        options=[
            AnalyticsOptionMetric(
                option_index=0,
                option_id="correct",
                text="Posterior-weighted loss.",
                selections=correct,
                correct=True,
            ),
            AnalyticsOptionMetric(
                option_index=1,
                option_id="prior",
                text="Largest prior class only.",
                selections=max(1, attempts - correct - 2),
                correct=False,
            ),
            AnalyticsOptionMetric(
                option_index=2,
                option_id="ignore",
                text="Ignore costs after prediction.",
                selections=2,
                correct=False,
            ),
        ],
    )
    gate = AnalyticsGateMetric(
        gate_id=f"lecture-{seed:02d}-evidence-gate",
        total_events=gate_checks,
        unique_learners=max(1, learners - 2),
        latest_activity=None,
        status_counts={"needs_evidence": gate_checks - passed, "passed": passed},
        attendance_split={"absent": max(1, gate_checks // 4), "present": gate_checks - max(1, gate_checks // 4)},
    )
    return LectureAnalyticsSummary(
        course_id=course_id,
        lecture_id=lecture_id,
        total_events=quiz.total_attempts + gate.total_events,
        quizzes=[quiz],
        gates=[gate],
    )


def _lecture_seed(lecture_id: str) -> int:
    match = re.search(r"(\d+)$", lecture_id)
    return max(1, int(match.group(1))) if match else 1
