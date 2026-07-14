from __future__ import annotations

from collections import Counter
from datetime import date
from uuid import UUID

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile

from lecturepilot.api_auth import (
    request_context,
    require_professor,
    require_course_manager,
    require_same_tenant,
)
from lecturepilot.audit import record_audit_event
from lecturepilot.course_access import (
    course_has_visible_lecture,
    lecture_views_for_context,
    resolve_course_lectures,
)
from lecturepilot.course_repository import CourseRepository, CourseRepositoryError
from lecturepilot.course_schedule_store import (
    list_course_workspaces,
    write_course_workspace,
)
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.course_workspace import resolve_course_workspace
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.models import (
    Course,
    CourseMaterialUploadResult,
    CourseMaterialUploadType,
    CourseWorkspaceResult,
    CourseWorkspaceSetupInput,
    Lecture,
    LectureScheduleProposal,
    SourceBundleEntry,
    SourceBundleManifest,
    TenantRole,
)
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.secure_upload import promote_course_upload, stage_course_upload
from lecturepilot.source_index import indexed_course_files
from lecturepilot.tenancy import TenantContext
from lecturepilot.workspace import WorkspacePolicy, WorkspacePolicyError


def register_course_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> None:
    @app.get("/courses")
    def courses(context: TenantContext = Depends(request_context)) -> list[dict]:
        require_same_tenant(context, course_tenant_id=course_tenant_id)
        if context.auth_mode == "session":
            repository = CourseRepository(app.state.database)
            candidates = (
                repository.list_all(tenant_id=course_tenant_id)
                if TenantRole.STUDENT in context.roles
                else repository.list_owned(
                    user_id=UUID(context.user_id), tenant_id=course_tenant_id
                )
            )
            return [
                course.model_dump()
                for course in candidates
                if course_has_visible_lecture(
                    app,
                    context,
                    course,
                    course_tenant_id=course_tenant_id,
                )
            ]
        stored = list_course_workspaces(app.state.canvas_workspace.workspace_root, course_tenant_id)
        workspaces_by_id = {workspace.course.id: workspace for workspace in stored}
        courses_by_id = {
            seeded_course.id: seeded_course,
            **{workspace.course.id: workspace.course for workspace in stored},
        }
        return [
            course.model_dump()
            for course in courses_by_id.values()
            if course_has_visible_lecture(
                app,
                context,
                course,
                course_tenant_id=course_tenant_id,
                lectures=(
                    workspaces_by_id[course.id].lectures if course.id in workspaces_by_id else None
                ),
                seeded_lectures=seeded_lectures,
            )
        ]

    @app.get("/courses/{course_id}/lectures")
    def lectures(
        course_id: str,
        context: TenantContext = Depends(request_context),
    ) -> list[dict]:
        course, lecture_items = resolve_course_lectures(
            app,
            course_id=course_id,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
        )
        return [
            item.model_dump(mode="json")
            for item in lecture_views_for_context(
                app,
                context,
                course,
                lecture_items,
                course_tenant_id=course_tenant_id,
            )
        ]

    @app.post("/admin/course-workspaces", response_model=CourseWorkspaceResult)
    def create_course_workspace(
        setup: CourseWorkspaceSetupInput,
        context: TenantContext = Depends(request_context),
    ) -> CourseWorkspaceResult:
        require_professor(context)
        database_course = None
        created_database_course = False
        if context.auth_mode == "session":
            try:
                repository = CourseRepository(app.state.database)
                database_course = (
                    repository.owned_course(
                        user_id=UUID(context.user_id),
                        tenant_id=course_tenant_id,
                        course_id=setup.course_id,
                    )
                    if setup.course_id
                    else repository.create(
                        user_id=UUID(context.user_id),
                        tenant_id=course_tenant_id,
                        setup=setup,
                        default_term=seeded_course.term,
                    )
                )
                created_database_course = setup.course_id is None
            except (CourseRepositoryError, ValueError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        workspace = resolve_course_workspace(
            setup,
            professor="Professor" if database_course else context.user_id,
            term=database_course.term if database_course else seeded_course.term,
            course=database_course,
        )
        try:
            course_root = app.state.canvas_workspace.course_media_root(workspace.course.id)
            with locked_course_state(course_root):
                return write_course_workspace(
                    course_root,
                    workspace,
                    replace_lectures=setup.replace_lectures,
                )
        except Exception:
            if database_course and created_database_course:
                CourseRepository(app.state.database).archive(
                    user_id=UUID(context.user_id),
                    tenant_id=course_tenant_id,
                    course_id=database_course.id,
                )
            raise

    @app.get("/courses/{course_id}/source-bundle", response_model=SourceBundleManifest)
    def source_bundle(
        course_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> SourceBundleManifest:
        _require_manager(context, request, course_id, course_tenant_id)
        layout = app.state.canvas_workspace.layout
        with locked_course_state(layout.course_root(course_id)):
            files = indexed_course_files(layout=layout, course_id=course_id)
        counts = Counter(item.kind for item in files)
        uploads = [
            CourseMaterialUploadType(suffix=suffix, kind=kind, max_bytes=max_bytes)
            for suffix, (kind, max_bytes) in sorted(
                WorkspacePolicy.allowed_course_material_uploads.items()
            )
        ]
        return SourceBundleManifest(
            course_id=course_id,
            files=[SourceBundleEntry(**item.__dict__) for item in files],
            counts_by_kind=dict(sorted(counts.items())),
            supported_uploads=uploads,
        )

    @app.get(
        "/admin/courses/{course_id}/lecture-schedule",
        response_model=LectureScheduleProposal,
    )
    async def lecture_schedule(
        course_id: str,
        request: Request,
        first_lecture_date: str | None = None,
        count: int | None = None,
        context: TenantContext = Depends(request_context),
    ) -> LectureScheduleProposal:
        _require_manager(context, request, course_id, course_tenant_id)
        roots = app.state.canvas_workspace.source_bundle_roots(
            course_id,
            include_seeded_materials=False,
        )
        try:
            start_date = date.fromisoformat(first_lecture_date) if first_lecture_date else None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid first lecture date.") from exc
        try:
            layout = app.state.canvas_workspace.layout
            with locked_course_state(layout.course_root(course_id)):
                files = indexed_course_files(layout=layout, course_id=course_id)
            with model_usage_scope(
                actor_user_id=context.user_id,
                course_id=course_id,
                workload="course_schedule",
            ):
                return await app.state.lecture_schedule_planner.propose_schedule(
                    course_id=course_id,
                    files=files,
                    roots=list(roots),
                    first_lecture_date=start_date,
                    requested_count=count,
                )
        except ProviderConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ModelExecutionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post(
        "/admin/courses/{course_id}/materials",
        response_model=CourseMaterialUploadResult,
    )
    async def upload_course_material(
        course_id: str,
        request: Request,
        path: str = Form(..., min_length=1, max_length=500),
        file: UploadFile = File(...),
        context: TenantContext = Depends(request_context),
    ) -> CourseMaterialUploadResult:
        try:
            _require_manager(context, request, course_id, course_tenant_id)
            layout = app.state.canvas_workspace.layout
            course_root = layout.course_root(course_id)
            staged = await stage_course_upload(
                file,
                quarantine_root=course_root.parent / ".upload-quarantine" / course_root.name,
                tenant_id=context.tenant_id,
                requested_path=path,
            )
            try:
                with locked_course_state(course_root):
                    _require_manager(context, request, course_id, course_tenant_id)
                    stored = promote_course_upload(
                        staged,
                        uploads_root=layout.course_uploads_dir(course_id),
                    )
                    indexed_course_files(
                        layout=layout,
                        course_id=course_id,
                        known_hashes={stored.path: stored.sha256},
                    )
            finally:
                staged.discard()
        except WorkspacePolicyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        record_audit_event(
            app.state.database,
            context,
            event_type="course.material_uploaded",
            target_type="course",
            target_id=course_id,
            details={"kind": stored.kind, "size_bytes": stored.size_bytes},
        )
        return CourseMaterialUploadResult(
            course_id=course_id,
            path=stored.path,
            kind=stored.kind,
            size_bytes=stored.size_bytes,
        )


def _require_manager(context, request, course_id, course_tenant_id) -> None:
    require_course_manager(
        context,
        course_tenant_id=course_tenant_id,
        request=request,
        course_id=course_id,
    )
