from __future__ import annotations

from collections import Counter
from datetime import date

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from lecturepilot.analytics import AnalyticsStore
from lecturepilot.analytics_routes import register_analytics_routes
from lecturepilot.admin_media_routes import register_admin_media_routes
from lecturepilot.api_auth import (
    request_context,
    require_course_manager,
)
from lecturepilot.agent_routes import register_agent_routes
from lecturepilot.canvas_workspace import CanvasWorkspace, CanvasWorkspaceError
from lecturepilot.canvas_workspace_config import SEEDED_COURSE_ID
from lecturepilot.course_builder_source import course_builder_source_document, scan_source_bundles
from lecturepilot.course_canvas_routes import register_course_canvas_routes
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.course_deletion import register_course_deletion_routes
from lecturepilot.course_schedule_store import list_course_workspaces, read_course_workspace, write_course_workspace
from lecturepilot.course_workspace import resolve_course_workspace
from lecturepilot.dev_seeded_course import discovered_seeded_lecture_views
from lecturepilot.exam_readiness_routes import register_exam_readiness_routes
from lecturepilot.harness import LecturePilotHarness
from lecturepilot.image_generation_registry import image_generator_from_env
from lecturepilot.lecture_schedule_planner import LectureSchedulePlanner
from lecturepilot.learner_state import LearnerStateStore
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import (
    CourseMaterialUploadResult,
    CourseMaterialUploadType,
    CourseWorkspaceResult,
    CourseWorkspaceSetupInput,
    LectureScheduleProposal,
    SourceBundleEntry,
    SourceBundleManifest,
    TuebingenLoginInput,
    TuebingenLoginResult,
)
from lecturepilot.observability import observability_from_env
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.runtime_env import load_project_env
from lecturepilot.sample_data import COURSE, LECTURES, unlocked_lectures
from lecturepilot.tenancy import TenantContext
from lecturepilot.tuebingen_adapter import (
    TuebingenCourseAdapter,
    TuebingenIntegrationUnavailable,
    TuebingenLoginError,
)
from lecturepilot.user_memory import UserMemoryStore
from lecturepilot.workspace import WorkspacePolicy, WorkspacePolicyError
from lecturepilot.youtube_discovery import YoutubeDiscovery


COURSE_TENANT_ID = "tenant-tuebingen"
load_project_env()


def create_app() -> FastAPI:
    app = FastAPI(title="LecturePilot API", version="0.1.0")
    app.state.tuebingen_adapter = TuebingenCourseAdapter()
    app.state.agent_harness = LecturePilotHarness()
    app.state.course_planner = CourseCanvasPlanner()
    app.state.lecture_schedule_planner = LectureSchedulePlanner()
    app.state.canvas_workspace = CanvasWorkspace()
    app.state.learner_state = LearnerStateStore(app.state.canvas_workspace.layout)
    app.state.user_memory_store = UserMemoryStore(app.state.canvas_workspace.layout)
    app.state.analytics_store = AnalyticsStore(app.state.canvas_workspace.layout)
    app.state.image_generator = image_generator_from_env()
    app.state.canvas_workspace.image_generator = app.state.image_generator
    app.state.youtube_discovery = YoutubeDiscovery.from_env()
    app.state.observability = observability_from_env()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    register_admin_media_routes(
        app,
        course=COURSE,
        lectures=LECTURES,
        course_tenant_id=COURSE_TENANT_ID,
    )
    register_agent_routes(app, course=COURSE, course_tenant_id=COURSE_TENANT_ID)
    register_analytics_routes(app, course_tenant_id=COURSE_TENANT_ID)
    register_course_canvas_routes(
        app,
        course_tenant_id=COURSE_TENANT_ID,
        lectures=LECTURES,
        seeded_course_id=SEEDED_COURSE_ID,
        source_document=lambda course_id, lecture_id: course_builder_source_document(
            app,
            course_id,
            lecture_id,
        ),
    )
    register_course_deletion_routes(app, course_tenant_id=COURSE_TENANT_ID)
    register_exam_readiness_routes(app, course_tenant_id=COURSE_TENANT_ID, lectures=LECTURES)

    @app.get("/courses")
    def courses() -> list[dict]:
        stored = list_course_workspaces(app.state.canvas_workspace.workspace_root, COURSE_TENANT_ID)
        courses_by_id = {COURSE.id: COURSE}
        courses_by_id.update({workspace.course.id: workspace.course for workspace in stored})
        return [course.model_dump() for course in courses_by_id.values()]

    @app.post("/auth/login", response_model=TuebingenLoginResult)
    def login(input_data: TuebingenLoginInput) -> TuebingenLoginResult:
        try:
            return app.state.tuebingen_adapter.login(
                username=input_data.username,
                password=input_data.password.get_secret_value(),
                term=input_data.term,
            )
        except TuebingenIntegrationUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except TuebingenLoginError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @app.get("/courses/{course_id}/lectures")
    def lectures(course_id: str) -> list[dict]:
        workspace = read_course_workspace(app.state.canvas_workspace.course_media_root(course_id), course_id)
        if workspace:
            return [
                {
                    "lecture": lecture.model_dump(mode="json"),
                    "unlocked": True,
                    "attendance": "unknown",
                }
                for lecture in workspace.lectures
            ]
        if discovered_lectures := discovered_seeded_lecture_views(
            course_id,
            app.state.canvas_workspace.material_root,
        ):
            return [item.model_dump(mode="json") for item in discovered_lectures]
        if course_id != COURSE.id:
            raise HTTPException(status_code=404, detail="Course not found.")
        return [item.model_dump(mode="json") for item in unlocked_lectures()]

    @app.post("/admin/course-workspaces", response_model=CourseWorkspaceResult)
    def create_course_workspace(
        setup: CourseWorkspaceSetupInput,
        context: TenantContext = Depends(request_context),
    ) -> CourseWorkspaceResult:
        require_course_manager(context, course_tenant_id=COURSE_TENANT_ID)
        workspace = resolve_course_workspace(
            setup,
            professor=context.user_id,
            term=COURSE.term,
        )
        workspace = write_course_workspace(
            app.state.canvas_workspace.course_media_root(workspace.course.id),
            workspace,
        )
        return workspace

    @app.get("/courses/{course_id}/source-bundle", response_model=SourceBundleManifest)
    def source_bundle(
        course_id: str,
        context: TenantContext = Depends(request_context),
    ) -> SourceBundleManifest:
        require_course_manager(context, course_tenant_id=COURSE_TENANT_ID)
        files = scan_source_bundles(
            app.state.canvas_workspace.source_bundle_roots(course_id, include_seeded_materials=False)
        )
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

    @app.get("/admin/courses/{course_id}/lecture-schedule", response_model=LectureScheduleProposal)
    async def lecture_schedule(
        course_id: str,
        first_lecture_date: str | None = None,
        count: int | None = None,
        context: TenantContext = Depends(request_context),
    ) -> LectureScheduleProposal:
        require_course_manager(context, course_tenant_id=COURSE_TENANT_ID)
        roots = app.state.canvas_workspace.source_bundle_roots(
            course_id,
            include_seeded_materials=False,
        )
        try:
            start_date = date.fromisoformat(first_lecture_date) if first_lecture_date else None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid first lecture date.") from exc
        try:
            return await app.state.lecture_schedule_planner.propose_schedule(
                course_id=course_id,
                files=scan_source_bundles(roots),
                roots=list(roots),
                first_lecture_date=start_date,
                requested_count=count,
            )
        except ProviderConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ModelExecutionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.post("/admin/courses/{course_id}/materials", response_model=CourseMaterialUploadResult)
    async def upload_course_material(
        course_id: str,
        path: str = Form(..., min_length=1, max_length=500),
        file: UploadFile = File(...),
        context: TenantContext = Depends(request_context),
    ) -> CourseMaterialUploadResult:
        try:
            require_course_manager(context, course_tenant_id=COURSE_TENANT_ID)
            payload = await file.read()
            checked = WorkspacePolicy().validate_course_material_upload(
                tenant_id=context.tenant_id,
                path=path,
                size_bytes=len(payload),
            )
        except WorkspacePolicyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        target = app.state.canvas_workspace.course_upload_path(course_id=course_id, path=path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return CourseMaterialUploadResult(
            course_id=course_id,
            path=path,
            kind=checked.kind,
            size_bytes=len(payload),
            storage_path=str(target),
        )

    @app.get("/course-assets/{course_id}/{lecture_id}/{asset_path:path}")
    def course_asset(
        course_id: str,
        lecture_id: str,
        asset_path: str,
        preview: str | None = None,
    ) -> FileResponse:
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
    ) -> FileResponse:
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

    return app

app = create_app()
