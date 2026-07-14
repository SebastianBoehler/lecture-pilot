from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

from lecturepilot.account_admin_routes import register_account_admin_routes
from lecturepilot.admin_media_routes import register_admin_media_routes
from lecturepilot.analytics import AnalyticsStore
from lecturepilot.analytics_routes import register_analytics_routes
from lecturepilot.asset_routes import register_asset_routes
from lecturepilot.agent_routes import register_agent_routes
from lecturepilot.auth_routes import register_auth_routes
from lecturepilot.body_limits import RequestBodyLimitMiddleware
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_builder_source import course_builder_source_document
from lecturepilot.course_canvas_routes import register_course_canvas_routes
from lecturepilot.course_canvas_planner import CourseCanvasPlanner, LiteLLMCoursePlanClient
from lecturepilot.course_deletion import register_course_deletion_routes
from lecturepilot.course_routes import register_course_routes
from lecturepilot.course_update_routes import register_course_update_routes
from lecturepilot.course_update_storage import CourseUpdateRecoveryError
from lecturepilot.csrf import CsrfProtectionMiddleware, allowed_origins
from lecturepilot.database import Database
from lecturepilot.exam_readiness_routes import register_exam_readiness_routes
from lecturepilot.harness import LecturePilotHarness
from lecturepilot.image_generation_registry import image_generator_from_env
from lecturepilot.lecture_schedule_planner import LectureSchedulePlanner, LiteLLMScheduleClient
from lecturepilot.lecture_access_routes import register_lecture_access_routes
from lecturepilot.model_client import LiteLLMModelClient
from lecturepilot.model_usage import ModelUsageRecorder
from lecturepilot.learner_state import LearnerStateStore
from lecturepilot.learner_profile_routes import register_learner_profile_routes
from lecturepilot.observability import observability_from_env
from lecturepilot.professor_usage import ProfessorUsageRepository
from lecturepilot.professor_usage_routes import register_professor_usage_routes
from lecturepilot.rate_limit import RateLimitMiddleware
from lecturepilot.release_info import release_info
from lecturepilot.runtime_env import load_project_env
from lecturepilot.sample_data import COURSE, LECTURES
from lecturepilot.security_headers import (
    SecurityHeadersMiddleware,
    allowed_hosts,
    production_fastapi_kwargs,
)
from lecturepilot.session_auth import SessionAuthSettings
from lecturepilot.session_store import SessionStore
from lecturepilot.tuebingen_adapter import TuebingenCourseAdapter
from lecturepilot.university_course_routes import register_university_course_routes
from lecturepilot.university_course_search import AlmaUniversityCourseSearch
from lecturepilot.user_memory import UserMemoryStore
from lecturepilot.usage_quota import UsageQuota
from lecturepilot.youtube_discovery import YoutubeDiscovery


COURSE_TENANT_ID = "tenant-tuebingen"
load_project_env()


def create_app() -> FastAPI:
    SessionAuthSettings.from_env()
    release = release_info()
    app = FastAPI(
        title="LecturePilot API",
        version=release.version,
        **production_fastapi_kwargs(),
    )

    @app.exception_handler(CourseUpdateRecoveryError)
    async def course_update_recovery_error(
        _request: Request, exc: CourseUpdateRecoveryError
    ) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    app.state.database = Database()
    app.state.session_store = SessionStore(app.state.database)
    app.state.usage_quota = UsageQuota(app.state.database)
    app.state.course_tenant_id = COURSE_TENANT_ID
    app.state.model_usage = ModelUsageRecorder(app.state.database, tenant_id=COURSE_TENANT_ID)
    app.state.professor_usage = ProfessorUsageRepository(app.state.database)
    app.state.observability = observability_from_env()
    app.state.tuebingen_adapter = TuebingenCourseAdapter()
    app.state.university_course_search = AlmaUniversityCourseSearch()
    app.state.agent_harness = LecturePilotHarness(
        model_client=LiteLLMModelClient(app.state.model_usage)
    )
    app.state.course_planner = CourseCanvasPlanner(
        model_client=LiteLLMCoursePlanClient(app.state.model_usage),
        observability=app.state.observability,
    )
    app.state.lecture_schedule_planner = LectureSchedulePlanner(
        model_client=LiteLLMScheduleClient(app.state.model_usage)
    )
    app.state.canvas_workspace = CanvasWorkspace()
    app.state.learner_state = LearnerStateStore(app.state.canvas_workspace.layout)
    app.state.user_memory_store = UserMemoryStore(app.state.canvas_workspace.layout)
    app.state.analytics_store = AnalyticsStore(app.state.canvas_workspace.layout)
    app.state.image_generator = image_generator_from_env()
    app.state.canvas_workspace.image_generator = app.state.image_generator
    app.state.youtube_discovery = YoutubeDiscovery.from_env()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins()),
        allow_credentials=True,
        allow_methods=["GET", "HEAD", "OPTIONS", "POST", "PUT", "DELETE"],
        allow_headers=[
            "Accept",
            "Authorization",
            "Content-Type",
            "X-Course-Ids",
            "X-CSRF-Token",
            "X-LecturePilot-Learner-Preview",
            "X-Tenant-Id",
            "X-User-Id",
            "X-User-Role",
        ],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts())
    app.add_middleware(RequestBodyLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CsrfProtectionMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/health")
    def health(response: Response) -> dict[str, str]:
        expected_commit = (os.getenv("LECTUREPILOT_COMMIT_SHA") or "").strip().lower()
        identity_matches = not expected_commit or expected_commit == release.commit_sha
        if not identity_matches:
            response.status_code = 503
        return {
            "status": "ok" if identity_matches else "error",
            "version": release.version,
            "commit_sha": release.commit_sha,
        }

    register_auth_routes(app, course_tenant_id=COURSE_TENANT_ID)
    register_university_course_routes(app, course_tenant_id=COURSE_TENANT_ID)
    register_account_admin_routes(app)
    register_learner_profile_routes(app, course_tenant_id=COURSE_TENANT_ID)
    register_admin_media_routes(
        app,
        course=COURSE,
        lectures=LECTURES,
        course_tenant_id=COURSE_TENANT_ID,
    )
    seeded_route_args = {
        "course_tenant_id": COURSE_TENANT_ID,
        "seeded_course": COURSE,
        "seeded_lectures": LECTURES,
    }
    register_agent_routes(app, **seeded_route_args)
    register_analytics_routes(app, **seeded_route_args)
    register_professor_usage_routes(app, course_tenant_id=COURSE_TENANT_ID)
    register_course_canvas_routes(
        app,
        course_tenant_id=COURSE_TENANT_ID,
        lectures=LECTURES,
        seeded_course=COURSE,
        source_document=lambda course_id, lecture_id: course_builder_source_document(
            app,
            course_id,
            lecture_id,
        ),
    )
    register_course_deletion_routes(app, course_tenant_id=COURSE_TENANT_ID)
    register_lecture_access_routes(
        app,
        course_tenant_id=COURSE_TENANT_ID,
        seeded_course=COURSE,
    )
    register_course_update_routes(app, course_tenant_id=COURSE_TENANT_ID)
    register_exam_readiness_routes(
        app,
        course_tenant_id=COURSE_TENANT_ID,
        seeded_course=COURSE,
        lectures=LECTURES,
    )
    register_asset_routes(app, **seeded_route_args)
    register_course_routes(
        app,
        course_tenant_id=COURSE_TENANT_ID,
        seeded_course=COURSE,
        seeded_lectures=LECTURES,
    )

    return app


app = create_app()
