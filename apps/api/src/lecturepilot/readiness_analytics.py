from __future__ import annotations

from collections import Counter

from pydantic import BaseModel

from lecturepilot.readiness_progress import ReadinessProgressStore


class ReadinessWeakSection(BaseModel):
    lecture_id: str
    section_id: str
    open_tasks: int


class CourseReadinessSummary(BaseModel):
    course_id: str
    total_attempts: int
    unique_learners: int
    task_status_counts: dict[str, int]
    weak_sections: list[ReadinessWeakSection]


def course_readiness_summary(
    *,
    course_id: str,
    store: ReadinessProgressStore,
) -> CourseReadinessSummary:
    records = store.list_course_progress(course_id=course_id)
    task_status_counts: Counter[str] = Counter()
    weak_sections: Counter[tuple[str, str]] = Counter()
    total_attempts = 0
    for _user_key, progress in records:
        total_attempts += len({event.attempt_id for event in progress.attempts})
        for task in progress.active_tasks:
            task_status_counts[task.status] += 1
            if task.status == "open":
                weak_sections[(task.lecture_id, task.section_id)] += 1
    return CourseReadinessSummary(
        course_id=course_id,
        total_attempts=total_attempts,
        unique_learners=len(records),
        task_status_counts=dict(sorted(task_status_counts.items())),
        weak_sections=[
            ReadinessWeakSection(lecture_id=lecture_id, section_id=section_id, open_tasks=count)
            for (lecture_id, section_id), count in sorted(weak_sections.items())
        ],
    )
