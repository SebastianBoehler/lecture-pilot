from __future__ import annotations

import re
from datetime import date

from lecturepilot.canvas_workspace_config import SEEDED_COURSE_ID
from lecturepilot.models import Course, CourseWorkspaceResult, CourseWorkspaceSetupInput, Lecture

SEEDED_COURSE_SLUGS = {"grundlagen-des-maschinellen-lernens"}


def resolve_course_workspace(
    setup: CourseWorkspaceSetupInput,
    *,
    professor: str,
    term: str,
    course: Course | None = None,
) -> CourseWorkspaceResult:
    if course is None:
        course = Course(
            access_policy=setup.access_policy,
            canvas_language=setup.canvas_language,
            id=_course_id(setup.course_title),
            title=setup.course_title.strip(),
            professor=professor,
            term=term,
        )
    else:
        if "canvas_language" in setup.model_fields_set:
            course = course.model_copy(update={"canvas_language": setup.canvas_language})
    lectures = _lectures_for_setup(setup, course.id)
    return CourseWorkspaceResult(
        course=course,
        lectures=lectures,
        active_lecture_id=lectures[0].id,
    )


def merge_course_workspace(
    existing: CourseWorkspaceResult | None,
    incoming: CourseWorkspaceResult,
    *,
    replace_lectures: bool = False,
) -> CourseWorkspaceResult:
    if existing is None or existing.course.id != incoming.course.id:
        return incoming
    course = incoming.course.model_copy(
        update={"default_publication_mode": existing.course.default_publication_mode}
    )
    incoming_by_id = {lecture.id: lecture for lecture in incoming.lectures}
    if replace_lectures:
        existing_by_id = {lecture.id: lecture for lecture in existing.lectures}
        return incoming.model_copy(
            update={
                "course": course,
                "lectures": [
                    _merge_lecture(existing_by_id.get(lecture.id), lecture)
                    for lecture in incoming.lectures
                ],
            }
        )
    merged = [
        _merge_lecture(lecture, incoming_by_id.get(lecture.id)) for lecture in existing.lectures
    ]
    existing_ids = {lecture.id for lecture in existing.lectures}
    merged.extend(lecture for lecture in incoming.lectures if lecture.id not in existing_ids)
    return incoming.model_copy(update={"course": course, "lectures": merged})


def _merge_lecture(existing: Lecture | None, incoming: Lecture | None) -> Lecture:
    if existing is None and incoming is not None:
        return incoming
    if existing is None:
        raise ValueError("A lecture is required.")
    if incoming is None:
        return existing
    if existing.material_path and not incoming.material_path:
        return existing
    updates = {}
    if existing.access_override and incoming.access_override is None:
        updates["access_override"] = existing.access_override
    return incoming.model_copy(update=updates)


def _lectures_for_setup(setup: CourseWorkspaceSetupInput, course_id: str) -> list[Lecture]:
    if setup.lectures:
        return [
            Lecture(
                id=_lecture_id(number=item.number, title=item.title),
                course_id=course_id,
                title=item.title.strip(),
                date=item.date,
                material_path=item.material_path,
            )
            for item in setup.lectures
        ]
    if setup.target == "full-course":
        count = setup.lecture_count or 1
        return [
            Lecture(
                id=f"lecture-{index:02d}",
                course_id=course_id,
                title=f"Lecture {index:02d}",
                date=date.today(),
            )
            for index in range(1, count + 1)
        ]
    number = (setup.lecture_number or "").strip()
    title = (setup.lecture_title or "").strip() or "Lecture"
    return [
        Lecture(
            id=_lecture_id(number=number, title=title),
            course_id=course_id,
            title=title,
            date=date.today(),
        )
    ]


def _lecture_id(*, number: str, title: str) -> str:
    digits = re.sub(r"\D+", "", number)
    if digits:
        return f"lecture-{int(digits):02d}"
    return f"lecture-{_slug(title)}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.lower()).strip("-")
    return (slug or "course")[:80]


def _course_id(course_title: str) -> str:
    title_slug = _slug(course_title)
    if title_slug in SEEDED_COURSE_SLUGS:
        return SEEDED_COURSE_ID
    return title_slug
