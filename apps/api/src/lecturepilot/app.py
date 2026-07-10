from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from lecturepilot.analytics import AnalyticsStore
from lecturepilot.analytics_routes import register_analytics_routes
from lecturepilot.admin_media_routes import register_admin_media_routes
from lecturepilot.approval_routes import register_approval_routes
from lecturepilot.asset_routes import register_asset_routes
from lecturepilot.agent_routes import register_agent_routes
from lecturepilot.auth_routes import register_auth_routes
from lecturepilot.body_limits import RequestBodyLimitMiddleware
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_builder_source import course_builder_source_document
from lecturepilot.course_canvas_routes import register_course_canvas_routes
from lecturepilot.course_canvas_planner import CourseCanvasPlanner
from lecturepilot.course_deletion import register_course_deletion_routes
from lecturepilot.course_routes import register_course_routes
from lecturepilot.csrf import CsrfProtectionMiddleware, allowed_origins
from lecturepilot.database import Database
from lecturepilot.exam_readiness_routes import register_exam_readiness_routes
from lecturepilot.harness import LecturePilotHarness
from lecturepilot.image_generation_registry import image_generator_from_env
from lecturepilot.lecture_schedule_planner import LectureSchedulePlanner
from lecturepilot.learner_state import LearnerStateStore
from lecturepilot.observability import observability_from_env
from lecturepilot.rate_limit import RateLimitMiddleware
from lecturepilot.runtime_env import load_project_env
from lecturepilot.sample_data import COURSE, LECTURES
from lecturepilot.security_headers import (
    SecurityHeadersMiddleware,
    allowed_hosts,
    production_fastapi_kwargs,
)
from lecturepilot.session_store import SessionStore
from lecturepilot.tuebingen_adapter import TuebingenCourseAdapter
from lecturepilot.user_memory import UserMemoryStore
from lecturepilot.usage_quota import UsageQuota
from lecturepilot.youtube_discovery import YoutubeDiscovery


COURSE_TENANT_ID = "tenant-tuebingen"
load_project_env()


def create_app() -> FastAPI:
    app = FastAPI(title="LecturePilot API", version="0.1.0", **production_fastapi_kwargs())
    app.state.database = Database()
    app.state.session_store = SessionStore(app.state.database)
    app.state.usage_quota = UsageQuota(app.state.database)
    app.state.course_tenant_id = COURSE_TENANT_ID
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
        allow_origins=list(allowed_origins()),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts())
    app.add_middleware(RequestBodyLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CsrfProtectionMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    register_auth_routes(app, course_tenant_id=COURSE_TENANT_ID)
    register_approval_routes(app)
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
