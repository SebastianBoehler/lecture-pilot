from fastapi import FastAPI

from lecturepilot.course_publication_visibility import published_canvas_is_ready
from lecturepilot.lecture_access_models import CourseAccessSummary, LectureAccessSummary
from lecturepilot.lecture_access_policy import (
    course_default_rule,
    effective_publication_at,
    effective_rule,
    release_status,
)
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture


def build_course_access_summary(
    app: FastAPI,
    workspace: CourseWorkspaceResult,
    *,
    course: Course | None = None,
) -> CourseAccessSummary:
    canonical = course or workspace.course
    return CourseAccessSummary(
        course_id=canonical.id,
        default_rule=course_default_rule(canonical),
        lectures=[
            build_lecture_access_summary(app, canonical, lecture) for lecture in workspace.lectures
        ],
    )


def build_lecture_access_summary(
    app: FastAPI,
    course: Course,
    lecture: Lecture,
) -> LectureAccessSummary:
    rule = effective_rule(course, lecture)
    return LectureAccessSummary(
        lecture_id=lecture.id,
        rule_source="lecture_override" if lecture.access_override else "course_default",
        rule=rule,
        effective_publication_at=effective_publication_at(lecture, rule),
        release_status=release_status(lecture, rule),
        content_ready=published_canvas_is_ready(
            app,
            invalid_as_unavailable=True,
            course_id=course.id,
            lecture_id=lecture.id,
        ),
    )
