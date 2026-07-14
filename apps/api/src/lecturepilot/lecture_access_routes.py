from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.api_auth import request_context, require_course_manager
from lecturepilot.audit import record_audit_event
from lecturepilot.course_access import resolve_course
from lecturepilot.course_repository import CourseRepository, CourseRepositoryError
from lecturepilot.course_schedule_store import (
    overwrite_course_workspace,
    read_course_workspace,
)
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.lecture_access_models import (
    CourseAccessSummary,
    LectureAccessRule,
    LectureAccessSummary,
    LectureAccessUpdate,
    PublicationMode,
)
from lecturepilot.lecture_access_policy import (
    course_default_rule,
    effective_publication_at,
    effective_rule,
    is_university_audience,
    release_status,
)
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture
from lecturepilot.tenancy import TenantContext


def register_lecture_access_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
) -> None:
    @app.get(
        "/admin/courses/{course_id}/access",
        response_model=CourseAccessSummary,
    )
    def get_course_access(
        course_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CourseAccessSummary:
        workspace = _owned_workspace(app, request, context, course_id, course_tenant_id)
        course = resolve_course(app, course_id=course_id, seeded_course=seeded_course)
        return build_course_access_summary(app, workspace, course=course)

    @app.put(
        "/admin/courses/{course_id}/access",
        response_model=CourseAccessSummary,
    )
    def update_course_access(
        course_id: str,
        update: LectureAccessUpdate,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CourseAccessSummary:
        if update.rule.publication_mode not in {
            PublicationMode.HIDDEN,
            PublicationMode.ON_LECTURE_DATE,
        }:
            raise HTTPException(
                status_code=400,
                detail="Course defaults support hidden or lecture-date publication only.",
            )
        _require_university_confirmation(update)
        with _locked_owned_workspace(app, request, context, course_id, course_tenant_id) as (
            course_root,
            workspace,
        ):
            before = course_default_rule(workspace.course)
            rule = update.rule.materialize()
            canonical = resolve_course(app, course_id=course_id, seeded_course=seeded_course)
            updated = workspace.model_copy(
                update={
                    "course": canonical.model_copy(
                        update={
                            "access_policy": rule.audience,
                            "default_publication_mode": rule.publication_mode,
                        }
                    )
                }
            )
            previous_db_policy = _update_database_policy(
                app,
                context,
                course_tenant_id,
                course_id,
                rule.audience,
            )
            try:
                overwrite_course_workspace(course_root, updated)
            except Exception:
                if previous_db_policy is not None:
                    _update_database_policy(
                        app,
                        context,
                        course_tenant_id,
                        course_id,
                        previous_db_policy,
                    )
                raise
        _audit_rule_change(
            app,
            context,
            event_type="course.access_default_changed",
            target_id=course_id,
            before=before,
            after=rule,
        )
        return build_course_access_summary(app, updated, course=updated.course)

    @app.put(
        "/admin/courses/{course_id}/lectures/{lecture_id}/access",
        response_model=LectureAccessSummary,
    )
    def update_lecture_access(
        course_id: str,
        lecture_id: str,
        update: LectureAccessUpdate,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> LectureAccessSummary:
        _require_university_confirmation(update)
        with _locked_owned_workspace(app, request, context, course_id, course_tenant_id) as (
            course_root,
            workspace,
        ):
            index, lecture = _lecture(workspace, lecture_id)
            before = lecture.access_override
            rule = update.rule.materialize()
            updated_lecture = lecture.model_copy(update={"access_override": rule})
            updated = _replace_lecture(workspace, index, updated_lecture)
            overwrite_course_workspace(course_root, updated)
        _audit_rule_change(
            app,
            context,
            event_type="lecture.access_override_changed",
            target_id=f"{course_id}:{lecture_id}",
            before=before,
            after=rule,
        )
        course = resolve_course(app, course_id=course_id, seeded_course=seeded_course)
        return build_lecture_access_summary(app, course, updated_lecture)

    @app.delete(
        "/admin/courses/{course_id}/lectures/{lecture_id}/access",
        response_model=LectureAccessSummary,
    )
    def clear_lecture_access(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> LectureAccessSummary:
        with _locked_owned_workspace(app, request, context, course_id, course_tenant_id) as (
            course_root,
            workspace,
        ):
            index, lecture = _lecture(workspace, lecture_id)
            updated_lecture = lecture.model_copy(update={"access_override": None})
            updated = _replace_lecture(workspace, index, updated_lecture)
            overwrite_course_workspace(course_root, updated)
        _audit_rule_change(
            app,
            context,
            event_type="lecture.access_override_cleared",
            target_id=f"{course_id}:{lecture_id}",
            before=lecture.access_override,
            after=None,
        )
        course = resolve_course(app, course_id=course_id, seeded_course=seeded_course)
        return build_lecture_access_summary(app, course, updated_lecture)


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
        content_ready=app.state.canvas_workspace.has_published_course_canvas(
            course_id=course.id,
            lecture_id=lecture.id,
        ),
    )


def _owned_workspace(app, request, context, course_id, tenant_id) -> CourseWorkspaceResult:
    require_course_manager(
        context,
        course_tenant_id=tenant_id,
        request=request,
        course_id=course_id,
    )
    workspace = read_course_workspace(_course_root(app, course_id), course_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Course workspace not found.")
    return workspace


@contextmanager
def _locked_owned_workspace(app, request, context, course_id, tenant_id):
    require_course_manager(
        context,
        course_tenant_id=tenant_id,
        request=request,
        course_id=course_id,
    )
    course_root = _course_root(app, course_id)
    with locked_course_state(course_root):
        workspace = read_course_workspace(course_root, course_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Course workspace not found.")
        yield course_root, workspace


def _course_root(app: FastAPI, course_id: str):
    return app.state.canvas_workspace.course_media_root(course_id)


def _lecture(workspace: CourseWorkspaceResult, lecture_id: str) -> tuple[int, Lecture]:
    for index, lecture in enumerate(workspace.lectures):
        if lecture.id == lecture_id:
            return index, lecture
    raise HTTPException(status_code=404, detail="Lecture not found.")


def _replace_lecture(
    workspace: CourseWorkspaceResult,
    index: int,
    lecture: Lecture,
) -> CourseWorkspaceResult:
    lectures = list(workspace.lectures)
    lectures[index] = lecture
    return workspace.model_copy(update={"lectures": lectures})


def _require_university_confirmation(update: LectureAccessUpdate) -> None:
    if is_university_audience(update.rule.audience) and not update.confirm_university_members:
        raise HTTPException(
            status_code=400,
            detail="University-wide access requires explicit confirmation.",
        )


def _update_database_policy(app, context, tenant_id, course_id, policy):
    if context.auth_mode != "session":
        return None
    try:
        return CourseRepository(app.state.database).update_access_policy(
            user_id=UUID(context.user_id),
            tenant_id=tenant_id,
            course_id=course_id,
            access_policy=policy,
        )
    except (CourseRepositoryError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _audit_rule_change(app, context, *, event_type, target_id, before, after) -> None:
    def payload(rule: LectureAccessRule | None):
        return rule.model_dump(mode="json") if rule else None

    record_audit_event(
        app.state.database,
        context,
        event_type=event_type,
        target_type="lecture" if ":" in target_id else "course",
        target_id=target_id,
        details={"before": payload(before), "after": payload(after)},
    )
