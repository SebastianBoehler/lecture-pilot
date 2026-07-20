from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException

from lecturepilot.course_repository import CourseRepository
from lecturepilot.course_schedule_store import read_course_workspace
from lecturepilot.dev_seeded_course import discovered_seeded_lecture_views
from lecturepilot.lecture_access_models import CourseAccessPolicy, LectureReleaseStatus
from lecturepilot.lecture_access_policy import (
    audience_allows,
    can_list_lecture,
    effective_publication_at,
    effective_rule,
    release_status,
)
from lecturepilot.models import AttendanceStatus, Course, Lecture, LectureView, TenantRole
from lecturepilot.tenancy import TenantContext


_COURSE_ACCESS_ROLES = frozenset({TenantRole.TENANT_ADMIN, TenantRole.PROFESSOR})


@dataclass(frozen=True)
class CourseActorAccess:
    is_owner: bool
    is_enrolled: bool
    same_tenant: bool


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
    return (
        course.access_policy is CourseAccessPolicy.TUEBINGEN_ENROLLED
        and course.id in context.course_ids
    )


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
    seeded_lectures: list[Lecture] | None = None,
) -> Course:
    course, lectures = resolve_course_lectures(
        app,
        course_id=course_id,
        seeded_course=seeded_course,
        seeded_lectures=seeded_lectures or [],
    )
    actor = course_actor_access(app, context, course_id, course_tenant_id)
    if actor.is_owner:
        return course
    if not any(
        audience_allows(effective_rule(course, lecture), **actor.__dict__) for lecture in lectures
    ):
        raise HTTPException(status_code=404, detail="Course not found.")
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
    lecture = next((item for item in lectures if item.id == lecture_id), None)
    if lecture is None:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    actor = course_actor_access(app, context, course_id, course_tenant_id)
    if actor.is_owner:
        return course, lecture
    if not app.state.canvas_workspace.has_published_course_canvas(
        course_id=course_id,
        lecture_id=lecture_id,
    ):
        raise HTTPException(status_code=404, detail="Lecture not found.")
    rule = effective_rule(course, lecture)
    if not audience_allows(rule, **actor.__dict__):
        raise HTTPException(status_code=404, detail="Lecture not found.")
    status = release_status(lecture, rule)
    if status is LectureReleaseStatus.HIDDEN:
        raise HTTPException(status_code=404, detail="Lecture not found.")
    if status is LectureReleaseStatus.SCHEDULED:
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
            workspace = _read_workspace(app, course_id)
            if workspace:
                return stored_course.model_copy(
                    update={
                        "canvas_language": workspace.course.canvas_language,
                        "default_publication_mode": workspace.course.default_publication_mode,
                    }
                )
            return stored_course
    workspace = _read_workspace(app, course_id)
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
    course = resolve_course(app, course_id=course_id, seeded_course=seeded_course)
    workspace = _read_workspace(app, course_id)
    if workspace:
        return course, workspace.lectures
    if course_id == seeded_course.id:
        material_root = getattr(app.state.canvas_workspace, "material_root", None)
        discovered = (
            discovered_seeded_lecture_views(course_id, material_root)
            if isinstance(material_root, Path)
            else []
        )
        if discovered:
            return course, [item.lecture for item in discovered]
        return course, seeded_lectures
    raise HTTPException(status_code=404, detail="Course not found.")


def lecture_views_for_context(
    app: FastAPI,
    context: TenantContext,
    course: Course,
    lectures: list[Lecture],
    *,
    course_tenant_id: str,
) -> list[LectureView]:
    actor = course_actor_access(app, context, course.id, course_tenant_id)
    views = []
    for lecture in lectures:
        ready = app.state.canvas_workspace.has_published_course_canvas(
            course_id=course.id,
            lecture_id=lecture.id,
        )
        if not can_list_lecture(course, lecture, content_ready=ready, **actor.__dict__):
            continue
        rule = effective_rule(course, lecture)
        status = release_status(lecture, rule)
        views.append(
            LectureView(
                lecture=lecture,
                unlocked=status is LectureReleaseStatus.RELEASED,
                attendance=AttendanceStatus.UNKNOWN,
                release_status=status,
                effective_publication_at=effective_publication_at(lecture, rule),
                content_ready=ready,
            )
        )
    return views


def course_has_visible_lecture(
    app: FastAPI,
    context: TenantContext,
    course: Course,
    *,
    course_tenant_id: str,
    lectures: list[Lecture] | None = None,
    seeded_lectures: list[Lecture] | None = None,
) -> bool:
    if lectures is None:
        try:
            course, lectures = resolve_course_lectures(
                app,
                course_id=course.id,
                seeded_course=course,
                seeded_lectures=seeded_lectures or [],
            )
        except HTTPException:
            return False
    return bool(
        lecture_views_for_context(
            app,
            context,
            course,
            lectures,
            course_tenant_id=course_tenant_id,
        )
    )


def course_actor_access(
    app: FastAPI,
    context: TenantContext,
    course_id: str,
    tenant_id: str,
) -> CourseActorAccess:
    same_tenant = context.tenant_id == tenant_id
    if context.auth_mode == "dev":
        return CourseActorAccess(
            is_owner=same_tenant and can_review_course(context),
            is_enrolled=same_tenant and course_id in context.course_ids,
            same_tenant=same_tenant,
        )
    repository = CourseRepository(app.state.database)
    user_id = _user_uuid(context.user_id)
    return CourseActorAccess(
        is_owner=same_tenant
        and repository.is_owner(user_id=user_id, tenant_id=tenant_id, course_id=course_id),
        is_enrolled=same_tenant
        and repository.is_enrolled(user_id=user_id, tenant_id=tenant_id, course_id=course_id),
        same_tenant=same_tenant,
    )


def can_review_course(context: TenantContext) -> bool:
    return context.auth_mode == "dev" and not context.roles.isdisjoint(_COURSE_ACCESS_ROLES)


def _read_workspace(app: FastAPI, course_id: str):
    course_root = _course_media_root(app, course_id)
    return read_course_workspace(course_root, course_id) if course_root else None


def _user_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Session user identity is invalid.") from exc


def _course_media_root(app: FastAPI, course_id: str) -> Path | None:
    canvas_workspace = getattr(app.state, "canvas_workspace", None)
    course_media_root = getattr(canvas_workspace, "course_media_root", None)
    return course_media_root(course_id) if callable(course_media_root) else None
