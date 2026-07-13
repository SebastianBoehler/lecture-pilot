from __future__ import annotations

import shutil
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from lecturepilot.api_auth import request_context, require_course_manager
from lecturepilot.course_repository import CourseRepository
from lecturepilot.course_schedule_store import list_course_workspaces, read_course_workspace
from lecturepilot.models import CourseWorkspaceResult
from lecturepilot.storage_layout import StorageLayout, StorageLayoutError, safe_id
from lecturepilot.tenancy import TenantContext


class CourseDeletionResult(BaseModel):
    course_id: str = Field(min_length=1)
    archived: bool


class ManagedCourseWorkspaceResult(CourseWorkspaceResult):
    published_lecture_ids: list[str]


def delete_course_workspace(
    *, layout: StorageLayout, course_id: str
) -> CourseDeletionResult | None:
    course_root = layout.course_root(course_id)
    if not course_root.exists():
        return None
    shutil.rmtree(course_root)
    return CourseDeletionResult(course_id=course_id, archived=True)


def register_course_deletion_routes(app: FastAPI, *, course_tenant_id: str) -> None:
    @app.get("/admin/courses", response_model=list[ManagedCourseWorkspaceResult])
    def created_courses(
        context: TenantContext = Depends(request_context),
    ) -> list[ManagedCourseWorkspaceResult]:
        if context.auth_mode == "session":
            repository = CourseRepository(app.state.database)
            owned = repository.list_owned(user_id=_user_id(context), tenant_id=course_tenant_id)
            workspaces = []
            for course in owned:
                workspace = read_course_workspace(
                    app.state.canvas_workspace.course_media_root(course.id), course.id
                )
                if workspace is not None:
                    workspaces.append(workspace)
            return [_with_publication_state(app, workspace) for workspace in workspaces]
        require_course_manager(context, course_tenant_id=course_tenant_id)
        return [
            _with_publication_state(app, workspace)
            for workspace in list_course_workspaces(
                app.state.canvas_workspace.workspace_root, course_tenant_id
            )
        ]

    @app.delete("/admin/courses/{course_id}", response_model=CourseDeletionResult)
    def delete_course(
        course_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CourseDeletionResult:
        require_course_manager(
            context,
            course_tenant_id=course_tenant_id,
            request=request,
            course_id=course_id,
        )
        if not _is_canonical_course_id(course_id):
            raise HTTPException(status_code=400, detail="Invalid course id.")
        if context.auth_mode == "session":
            archived = CourseRepository(app.state.database).archive(
                user_id=_user_id(context),
                tenant_id=course_tenant_id,
                course_id=course_id,
            )
            if not archived:
                raise HTTPException(status_code=404, detail="Course was not found.")
            return CourseDeletionResult(course_id=course_id, archived=True)
        result = delete_course_workspace(
            layout=app.state.canvas_workspace.layout,
            course_id=course_id,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Course workspace not found.")
        return result


def _is_canonical_course_id(course_id: str) -> bool:
    try:
        return safe_id(course_id) == course_id
    except StorageLayoutError:
        return False


def _user_id(context: TenantContext) -> UUID:
    try:
        return UUID(context.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Database account is required.") from exc


def _with_publication_state(
    app: FastAPI,
    workspace: CourseWorkspaceResult,
) -> ManagedCourseWorkspaceResult:
    published = [
        lecture.id
        for lecture in workspace.lectures
        if app.state.canvas_workspace.has_published_course_canvas(
            course_id=workspace.course.id,
            lecture_id=lecture.id,
        )
    ]
    return ManagedCourseWorkspaceResult(
        **workspace.model_dump(),
        published_lecture_ids=published,
    )
