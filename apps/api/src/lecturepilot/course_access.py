from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException

from lecturepilot.course_schedule_store import read_course_workspace
from lecturepilot.course_repository import CourseRepository
from lecturepilot.dev_seeded_course import discovered_seeded_lecture_views
from lecturepilot.models import (
    AttendanceStatus,
    Course,
    CourseAccessPolicy,
    Lecture,
    LectureView,
    TenantRole,
)
from lecturepilot.policies import is_lecture_unlocked
from lecturepilot.tenancy import TenantContext


_COURSE_ACCESS_ROLES = frozenset({TenantRole.TENANT_ADMIN, TenantRole.PROFESSOR, TenantRole.TUTOR})


def filter_accessible_courses(
    context: TenantContext,
    courses: list[Course],
    *,
    course_tenant_id: str,
) -> list[Course]:
    return [
        course
        for course in courses
        if can_access_course(context, course=course, course_tenant_id=course_tenant_id)
    ]


def can_access_course(
    context: TenantContext,
    *,
    course: Course,
    course_tenant_id: str,
) -> bool:
    if context.tenant_id != course_tenant_id:
        return False
    if can_review_course(context):
        return True
    if course.access_policy in {
        CourseAccessPolicy.PUBLIC,
        CourseAccessPolicy.PLATFORM_AUTHENTICATED,
    }:
        return True
    return course.id in context.course_ids


def require_course_access(
    context: TenantContext,
    *,
    course: Course,
    course_tenant_id: str,
) -> None:
    if context.tenant_id != course_tenant_id:
        raise HTTPException(
            status_code=403, detail="Resource does not belong to the active tenant."
        )
    if not can_access_course(context, course=course, course_tenant_id=course_tenant_id):
        raise HTTPException(status_code=403, detail="Course enrollment is required.")


def require_course_id_access(
    app: FastAPI,
    context: TenantContext,
    *,
    course_id: str,
    course_tenant_id: str,
    seeded_course: Course,
) -> Course:
    course = resolve_course(app, course_id=course_id, seeded_course=seeded_course)
    if context.auth_mode == "session" and not CourseRepository(app.state.database).can_learn(
        user_id=_user_uuid(context.user_id),
        tenant_id=course_tenant_id,
        course_id=course_id,
    ):
        raise HTTPException(status_code=403, detail="Course enrollment is required.")
    require_course_access(context, course=course, course_tenant_id=course_tenant_id)
    return course


def require_lecture_id_access(
    app: FastAPI,
    context: TenantContext,
    *,
    course_id: str,
    lecture_id: str,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> tuple[Course, Lecture]:
    course, lectures = resolve_course_lectures(
        app,
        course_id=course_id,
        seeded_course=seeded_course,
        seeded_lectures=seeded_lectures,
    )
    require_course_access(context, course=course, course_tenant_id=course_tenant_id)
    lecture = next((item for item in lectures if item.id == lecture_id), None)
    if lecture is None:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    review = _can_review_course(app, context, course_id, course_tenant_id)
    if not review and not is_lecture_unlocked(lecture):
        raise HTTPException(status_code=403, detail="Lecture is not unlocked yet.")
    return course, lecture


def resolve_course(app: FastAPI, *, course_id: str, seeded_course: Course) -> Course:
    database = getattr(app.state, "database", None)
    if database is not None and database.configured:
        stored_course = CourseRepository(database).get(
            course_id=course_id,
            tenant_id=getattr(app.state, "course_tenant_id", "tenant-tuebingen"),
        )
        if stored_course:
            return stored_course
    course_root = _course_media_root(app, course_id)
    if course_root:
        workspace = read_course_workspace(course_root, course_id)
        if workspace:
            return workspace.course
    if course_id == seeded_course.id:
        return seeded_course
    raise HTTPException(status_code=404, detail="Course not found.")


def resolve_course_lectures(
    app: FastAPI,
    *,
    course_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> tuple[Course, list[Lecture]]:
    course_root = _course_media_root(app, course_id)
    if course_root:
        workspace = read_course_workspace(course_root, course_id)
        if workspace:
            return workspace.course, workspace.lectures
    if course_id == seeded_course.id:
        material_root = getattr(app.state.canvas_workspace, "material_root", None)
        discovered = (
            discovered_seeded_lecture_views(course_id, material_root)
            if isinstance(material_root, Path)
            else []
        )
        if discovered:
            return seeded_course, [item.lecture for item in discovered]
        return seeded_course, seeded_lectures
    raise HTTPException(status_code=404, detail="Course not found.")


def lecture_views_for_context(context: TenantContext, lectures: list[Lecture]) -> list[LectureView]:
    views = []
    for lecture in lectures:
        unlocked = is_lecture_unlocked(lecture)
        if not unlocked and not can_review_course(context):
            continue
        views.append(
            LectureView(
                lecture=lecture,
                unlocked=unlocked,
                attendance=AttendanceStatus.UNKNOWN,
            )
        )
    return views


def can_review_course(context: TenantContext) -> bool:
    return context.auth_mode == "dev" and not context.roles.isdisjoint(_COURSE_ACCESS_ROLES)


def _can_review_course(
    app: FastAPI,
    context: TenantContext,
    course_id: str,
    tenant_id: str,
) -> bool:
    if can_review_course(context):
        return True
    if context.auth_mode != "session":
        return False
    return CourseRepository(app.state.database).is_owner(
        user_id=_user_uuid(context.user_id),
        tenant_id=tenant_id,
        course_id=course_id,
    )


def _user_uuid(value: str):
    from uuid import UUID

    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Session user identity is invalid.") from exc


def _course_media_root(app: FastAPI, course_id: str) -> Path | None:
    canvas_workspace = getattr(app.state, "canvas_workspace", None)
    course_media_root = getattr(canvas_workspace, "course_media_root", None)
    if not callable(course_media_root):
        return None
    return course_media_root(course_id)
