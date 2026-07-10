from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse

from lecturepilot.api_auth import request_context, require_same_tenant
from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.course_access import require_lecture_id_access
from lecturepilot.models import Course, Lecture
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
        require_lecture_id_access(
            app,
            context,
            course_id=course_id,
            lecture_id=lecture_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
        )
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
        _require_workspace_asset_access(app, context=context, student_key=student_key)
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
    context: TenantContext,
    student_key: str,
) -> None:
    if app.state.canvas_workspace.layout.user_key(context.user_id) == student_key:
        return
    raise HTTPException(
        status_code=403,
        detail="Workspace asset does not belong to the active user.",
    )
