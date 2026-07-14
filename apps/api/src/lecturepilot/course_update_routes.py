from __future__ import annotations

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile

from lecturepilot.api_auth import request_context, require_course_manager
from lecturepilot.audit import record_audit_event
from lecturepilot.course_update import (
    CourseUpdateError,
    create_course_update,
    discard_course_update,
    require_update_accepting_uploads,
    update_uploads_dir,
)
from lecturepilot.course_update_analysis import analyze_course_update
from lecturepilot.course_update_apply import apply_course_update
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.course_update_storage import CourseUpdateRecoveryError
from lecturepilot.course_update_models import (
    CourseUpdateAnalysis,
    CourseUpdateApplyInput,
    CourseUpdateApplyResult,
    CourseUpdateCreated,
    CourseUpdateUploadResult,
)
from lecturepilot.secure_upload import promote_course_upload, stage_course_upload
from lecturepilot.tenancy import TenantContext
from lecturepilot.workspace import WorkspacePolicyError
from lecturepilot.workspace_fs import WorkspaceFSError


def register_course_update_routes(app: FastAPI, *, course_tenant_id: str) -> None:
    @app.post(
        "/admin/courses/{course_id}/updates",
        response_model=CourseUpdateCreated,
    )
    def create_update(
        course_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CourseUpdateCreated:
        _require_manager(request, context, course_id, course_tenant_id)
        try:
            update_id = create_course_update(app.state.canvas_workspace.layout, course_id)
        except CourseUpdateError as exc:
            raise _http_error(exc) from exc
        return CourseUpdateCreated(course_id=course_id, update_id=update_id)

    @app.post(
        "/admin/courses/{course_id}/updates/{update_id}/materials",
        response_model=CourseUpdateUploadResult,
    )
    async def upload_update_material(
        course_id: str,
        update_id: str,
        request: Request,
        path: str = Form(..., min_length=1, max_length=500),
        file: UploadFile = File(...),
        context: TenantContext = Depends(request_context),
    ) -> CourseUpdateUploadResult:
        _require_manager(request, context, course_id, course_tenant_id)
        layout = app.state.canvas_workspace.layout
        try:
            course_root = layout.course_root(course_id)
            staged = await stage_course_upload(
                file,
                quarantine_root=course_root.parent / ".upload-quarantine" / course_root.name,
                tenant_id=context.tenant_id,
                requested_path=path,
            )
            try:
                with locked_course_state(course_root):
                    require_update_accepting_uploads(layout, course_id, update_id)
                    uploads = update_uploads_dir(layout, course_id, update_id)
                    stored = promote_course_upload(staged, uploads_root=uploads)
            finally:
                staged.discard()
            # Build the index once during analysis; rescanning here makes folder uploads quadratic.
        except CourseUpdateError as exc:
            raise _http_error(exc) from exc
        except (WorkspacePolicyError, WorkspaceFSError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return CourseUpdateUploadResult(
            update_id=update_id,
            path=stored.path,
            kind=stored.kind,
            size_bytes=stored.size_bytes,
        )

    @app.get(
        "/admin/courses/{course_id}/updates/{update_id}",
        response_model=CourseUpdateAnalysis,
    )
    def update_analysis(
        course_id: str,
        update_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CourseUpdateAnalysis:
        _require_manager(request, context, course_id, course_tenant_id)
        try:
            layout = app.state.canvas_workspace.layout
            with locked_course_state(layout.course_root(course_id)):
                return analyze_course_update(layout, course_id, update_id)
        except CourseUpdateError as exc:
            raise _http_error(exc) from exc
        except WorkspaceFSError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post(
        "/admin/courses/{course_id}/updates/{update_id}/apply",
        response_model=CourseUpdateApplyResult,
    )
    def apply_update(
        course_id: str,
        update_id: str,
        payload: CourseUpdateApplyInput,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CourseUpdateApplyResult:
        _require_manager(request, context, course_id, course_tenant_id)
        try:
            result = apply_course_update(
                app.state.canvas_workspace.layout, course_id, update_id, payload
            )
        except CourseUpdateRecoveryError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except CourseUpdateError as exc:
            raise _http_error(exc) from exc
        except WorkspaceFSError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        record_audit_event(
            app.state.database,
            context,
            event_type="course.material_update_applied",
            target_type="course",
            target_id=course_id,
            details={
                "applied_files": result.applied_files,
                "affected_lectures": len(result.affected_lecture_ids),
            },
        )
        return result

    @app.delete(
        "/admin/courses/{course_id}/updates/{update_id}",
        status_code=204,
    )
    def discard_update(
        course_id: str,
        update_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> Response:
        _require_manager(request, context, course_id, course_tenant_id)
        try:
            discard_course_update(app.state.canvas_workspace.layout, course_id, update_id)
        except CourseUpdateError as exc:
            raise _http_error(exc) from exc
        return Response(status_code=204)


def _require_manager(request, context, course_id, course_tenant_id) -> None:
    require_course_manager(
        context,
        course_tenant_id=course_tenant_id,
        request=request,
        course_id=course_id,
    )


def _http_error(exc: CourseUpdateError) -> HTTPException:
    status = 404 if "not found" in str(exc).casefold() else 400
    return HTTPException(status_code=status, detail=str(exc))
