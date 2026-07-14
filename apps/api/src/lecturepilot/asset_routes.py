from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from lecturepilot.api_auth import request_context, require_course_owner, require_same_tenant
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.course_access import course_actor_access, require_lecture_id_access
from lecturepilot.models import Course, Lecture
from lecturepilot.professor_preview import professor_preview_user_id
from lecturepilot.tenancy import TenantContext


def register_asset_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> None:
    @app.get("/course-assets/{course_id}/{lecture_id}/{asset_path:path}")
    def course_asset(
        course_id: str,
        lecture_id: str,
        asset_path: str,
        preview: str | None = None,
        context: TenantContext = Depends(request_context),
    ) -> FileResponse:
        course, _lecture = require_lecture_id_access(
            app,
            context,
            course_id=course_id,
            lecture_id=lecture_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
        )
        actor = course_actor_access(app, context, course_id, course_tenant_id)
        if not actor.is_owner:
            _require_published_canvas_asset(app, course.id, lecture_id, asset_path)
        try:
            if preview == "png":
                path = app.state.canvas_workspace.asset_preview_path(
                    course_id=course_id,
                    lecture_id=lecture_id,
                    asset_path=asset_path,
                )
            else:
                path = app.state.canvas_workspace.asset_path(
                    course_id=course_id,
                    lecture_id=lecture_id,
                    asset_path=asset_path,
                )
        except CanvasWorkspaceError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return FileResponse(path)

    @app.get("/workspace-assets/{course_id}/{lecture_id}/{student_key}/{asset_path:path}")
    def workspace_asset(
        course_id: str,
        lecture_id: str,
        student_key: str,
        asset_path: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> FileResponse:
        require_same_tenant(context, course_tenant_id=course_tenant_id)
        require_lecture_id_access(
            app,
            context,
            course_id=course_id,
            lecture_id=lecture_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
        )
        _require_workspace_asset_access(
            app,
            request=request,
            context=context,
            course_id=course_id,
            course_tenant_id=course_tenant_id,
            student_key=student_key,
        )
        try:
            path = app.state.canvas_workspace.workspace_asset_path(
                course_id=course_id,
                lecture_id=lecture_id,
                student_key=student_key,
                asset_path=asset_path,
            )
        except CanvasWorkspaceError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return FileResponse(path)


def _require_workspace_asset_access(
    app: FastAPI,
    *,
    request: Request,
    context: TenantContext,
    course_id: str,
    course_tenant_id: str,
    student_key: str,
) -> None:
    if app.state.canvas_workspace.layout.user_key(context.user_id) == student_key:
        return
    preview_user_id = professor_preview_user_id(context.user_id, course_id)
    if app.state.canvas_workspace.layout.user_key(preview_user_id) == student_key:
        require_course_owner(
            request,
            context,
            course_id=course_id,
            course_tenant_id=course_tenant_id,
        )
        return
    raise HTTPException(
        status_code=403,
        detail="Workspace asset does not belong to the active user.",
    )


def _require_published_canvas_asset(
    app: FastAPI,
    course_id: str,
    lecture_id: str,
    asset_path: str,
) -> None:
    document = app.state.canvas_workspace.course_canvas_store.read(
        course_id=course_id,
        lecture_id=lecture_id,
        workspace_path="asset-authorization/index.md",
    )
    if document is None or asset_path not in _referenced_course_assets(document):
        raise HTTPException(status_code=404, detail="Canvas asset was not found.")


def _referenced_course_assets(document: CanvasDocument) -> set[str]:
    prefix = f"/course-assets/{document.course_id}/{document.lecture_id}/"
    referenced: set[str] = set()
    for section in document.sections:
        for block in section.blocks:
            if block.asset_path:
                referenced.add(block.asset_path.removeprefix("asset:"))
            if block.asset_url and block.asset_url.startswith(prefix):
                referenced.add(block.asset_url.removeprefix(prefix))
    return referenced
