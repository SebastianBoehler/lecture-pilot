from __future__ import annotations

from collections import Counter

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from lecturepilot.admin_media_routes import register_admin_media_routes
from lecturepilot.agent_routes import register_agent_routes
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.canvas_workspace import CanvasWorkspace, CanvasWorkspaceError
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.harness import LecturePilotHarness
from lecturepilot.image_generation_registry import image_generator_from_env
from lecturepilot.learner_state import LearnerStateStore
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import (
    CourseMaterialUploadResult,
    CourseMaterialUploadType,
    SourceBundleEntry,
    SourceBundleManifest,
    TenantRole,
    TuebingenLoginInput,
    TuebingenLoginResult,
)
from lecturepilot.observability import observability_from_env
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.sample_data import COURSE, LECTURES, unlocked_lectures
from lecturepilot.source_bundle import scan_source_bundle
from lecturepilot.tenancy import TenantAccessError, TenantContext, assert_can_upload_course_material
from lecturepilot.tuebingen_adapter import (
    TuebingenCourseAdapter,
    TuebingenIntegrationUnavailable,
    TuebingenLoginError,
)
from lecturepilot.user_memory import UserMemoryStore
from lecturepilot.workspace import WorkspacePolicy, WorkspacePolicyError
from lecturepilot.youtube_discovery import YoutubeDiscovery


COURSE_TENANT_ID = "tenant-tuebingen"


def create_app() -> FastAPI:
    app = FastAPI(title="LecturePilot API", version="0.1.0")
    app.state.tuebingen_adapter = TuebingenCourseAdapter()
    app.state.agent_harness = LecturePilotHarness()
    app.state.course_planner = CourseCanvasPlanner()
    app.state.canvas_workspace = CanvasWorkspace()
    app.state.learner_state = LearnerStateStore(app.state.canvas_workspace.layout)
    app.state.user_memory_store = UserMemoryStore(app.state.canvas_workspace.layout)
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
    register_agent_routes(app, course=COURSE)

    @app.get("/courses")
    def courses() -> list[dict]:
        return [COURSE.model_dump()]

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
        if course_id != COURSE.id:
            raise HTTPException(status_code=404, detail="Course not found.")
        return [item.model_dump(mode="json") for item in unlocked_lectures()]

    @app.get("/courses/{course_id}/source-bundle", response_model=SourceBundleManifest)
    def source_bundle(course_id: str) -> SourceBundleManifest:
        if course_id != COURSE.id:
            raise HTTPException(status_code=404, detail="Course not found.")
        files = _scan_source_bundles(app.state.canvas_workspace.source_bundle_roots(course_id))
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

    @app.post("/admin/courses/{course_id}/materials", response_model=CourseMaterialUploadResult)
    async def upload_course_material(
        course_id: str,
        path: str = Form(..., min_length=1, max_length=500),
        file: UploadFile = File(...),
        x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
        x_user_id: str = Header(..., alias="X-User-Id"),
        x_user_role: TenantRole = Header(..., alias="X-User-Role"),
    ) -> CourseMaterialUploadResult:
        if course_id != COURSE.id:
            raise HTTPException(status_code=404, detail="Course not found.")
        context = TenantContext(
            tenant_id=x_tenant_id,
            user_id=x_user_id,
            roles=frozenset({x_user_role}),
        )
        try:
            assert_can_upload_course_material(context, course_tenant_id=COURSE_TENANT_ID)
            payload = await file.read()
            checked = WorkspacePolicy().validate_course_material_upload(
                tenant_id=x_tenant_id,
                path=path,
                size_bytes=len(payload),
            )
        except TenantAccessError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
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

    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/draft",
        response_model=CanvasDocument,
    )
    async def draft_course_canvas(
        course_id: str,
        lecture_id: str,
        x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
        x_user_id: str = Header(..., alias="X-User-Id"),
        x_user_role: TenantRole = Header(..., alias="X-User-Role"),
    ) -> CanvasDocument:
        if course_id != COURSE.id:
            raise HTTPException(status_code=404, detail="Course not found.")
        if lecture_id not in {lecture.id for lecture in LECTURES}:
            raise HTTPException(status_code=404, detail="Lecture not found.")
        context = TenantContext(
            tenant_id=x_tenant_id,
            user_id=x_user_id,
            roles=frozenset({x_user_role}),
        )
        try:
            assert_can_upload_course_material(context, course_tenant_id=COURSE_TENANT_ID)
            source = app.state.canvas_workspace.source_document(
                course_id=course_id,
                lecture_id=lecture_id,
                workspace_path=f"course-planner/{lecture_id}/source.json",
            )
            document = await app.state.course_planner.plan_canvas(source)
            return app.state.canvas_workspace.write_course_canvas(document)
        except TenantAccessError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except CanvasWorkspaceError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ProviderConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ModelExecutionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.get("/courses/{course_id}/lectures/{lecture_id}/canvas")
    def lecture_canvas(course_id: str, lecture_id: str, user_id: str) -> dict:
        if course_id != COURSE.id:
            raise HTTPException(status_code=404, detail="Course not found.")
        try:
            document = app.state.canvas_workspace.read_document(
                course_id=course_id,
                lecture_id=lecture_id,
                user_id=user_id,
            )
        except CanvasWorkspaceError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return document.model_dump()

    @app.get("/course-assets/{course_id}/{lecture_id}/{asset_path:path}")
    def course_asset(
        course_id: str,
        lecture_id: str,
        asset_path: str,
        preview: str | None = None,
    ) -> FileResponse:
        if course_id != COURSE.id:
            raise HTTPException(status_code=404, detail="Course not found.")
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
        if course_id != COURSE.id:
            raise HTTPException(status_code=404, detail="Course not found.")
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


def _scan_source_bundles(roots) -> list:
    files_by_path = {}
    for root in roots:
        for item in scan_source_bundle(root):
            files_by_path.setdefault(item.path, item)
    return list(files_by_path.values())

app = create_app()
