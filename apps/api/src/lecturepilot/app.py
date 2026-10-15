from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from lecturepilot.identity.account_admin_routes import register_account_admin_routes
from lecturepilot.courses.admin_media_routes import register_admin_media_routes
from lecturepilot.analytics.analytics import AnalyticsStore
from lecturepilot.analytics.analytics_routes import register_analytics_routes
from lecturepilot.core.app_exception_handlers import register_exception_handlers
from lecturepilot.canvas.asset_routes import register_asset_routes
from lecturepilot.tutor.agent_routes import register_agent_routes
from lecturepilot.learner.attendance_routes import register_attendance_routes
from lecturepilot.identity.auth_routes import register_auth_routes
from lecturepilot.core.body_limits import RequestBodyLimitMiddleware
from lecturepilot.canvas.canvas_workspace import CanvasWorkspace
from lecturepilot.canvas.canvas_prediction_routes import register_canvas_prediction_routes
from lecturepilot.canvas.canvas_annotation_routes import register_canvas_annotation_routes
from lecturepilot.core.client_contract import CLIENT_CONTRACT_HEADER
from lecturepilot.storage_migrations import migrate_storage_on_startup
from lecturepilot.sources.course_builder_source import course_builder_source_document
from lecturepilot.authoring.course_canvas_routes import register_course_canvas_routes
from lecturepilot.authoring.authoring_runtime import CourseCanvasAuthor
from lecturepilot.learning_design.course_practice_design_planner import PracticeDesignPlanner
from lecturepilot.learning_design.course_practice_design_review_client import (
    NativePracticeDesignReviewClient,
)
from lecturepilot.courses.course_deletion import register_course_deletion_routes
from lecturepilot.courses.course_routes import register_course_routes
from lecturepilot.courses.course_support_routes import register_course_support_routes
from lecturepilot.sources.course_source_routing_routes import register_course_source_routing_routes
from lecturepilot.sources.course_source_routing_client import NativeSourceRoutingClient
from lecturepilot.sources.course_source_routing_planner import CourseSourceRoutingPlanner
from lecturepilot.courses.course_update_routes import register_course_update_routes
from lecturepilot.identity.csrf import CsrfProtectionMiddleware, allowed_origins
from lecturepilot.database import Database
from lecturepilot.exams.exam_readiness_routes import register_exam_readiness_routes
from lecturepilot.exams.practice_exam_attempt_routes import register_practice_exam_attempt_routes
from lecturepilot.exams.exam_answer_evaluation import (
    NativeOpenAnswerEvaluationClient,
    OpenAnswerEvaluator,
)
from lecturepilot.tutor.harness import LecturePilotHarness
from lecturepilot.llm.image_generation_registry import image_generator_from_env
from lecturepilot.courses.lecture_schedule_planner import (
    LectureSchedulePlanner,
    NativeScheduleClient,
)
from lecturepilot.courses.lecture_access_routes import register_lecture_access_routes
from lecturepilot.llm.model_client import NativeModelClient
from lecturepilot.llm.model_usage import ModelUsageRecorder
from lecturepilot.learner.learner_state import LearnerStateStore
from lecturepilot.learner.learner_lesson_state_routes import register_learner_lesson_state_routes
from lecturepilot.learner.learner_profile_routes import register_learner_profile_routes
from lecturepilot.learner.learner_study_routes import register_learner_study_routes
from lecturepilot.core.metadata_events import configure_metadata_file_logging, emit_metadata_event
from lecturepilot.core.observability import observability_from_env
from lecturepilot.llm.professor_usage import ProfessorUsageRepository
from lecturepilot.llm.professor_usage_routes import register_professor_usage_routes
from lecturepilot.exams.practice_exam_generation_jobs import PracticeExamGenerationStore
from lecturepilot.exams.practice_exam_planner import NativePracticeExamClient, PracticeExamPlanner
from lecturepilot.exams.practice_exam_pdf import PracticeExamPdfService
from lecturepilot.exams.practice_exam_routes import register_practice_exam_routes
from lecturepilot.exams.practice_exam_solution_routes import register_practice_exam_solution_routes
from lecturepilot.exams.practice_exam_store import PracticeExamStore
from lecturepilot.courses.course_invites import register_course_invite_routes
from lecturepilot.core.rate_limit import RateLimitMiddleware
from lecturepilot.release_info import release_info
from lecturepilot.core.request_diagnostics import RequestDiagnosticsMiddleware
from lecturepilot.core.runtime_readiness import RuntimeReadiness
from lecturepilot.learner.review_queue_routes import register_review_queue_routes
from lecturepilot.runtime_env import load_project_env
from lecturepilot.courses.sample_data import COURSE, LECTURES
from lecturepilot.core.security_headers import (
    SecurityHeadersMiddleware,
    allowed_hosts,
    production_fastapi_kwargs,
)
from lecturepilot.identity.session_auth import SessionAuthSettings
from lecturepilot.identity.session_cookie_refresh import SessionCookieRefreshMiddleware
from lecturepilot.identity.session_store import SessionStore
from lecturepilot.courses.university_course_routes import register_university_course_routes
from lecturepilot.courses.university_course_search import AlmaUniversityCourseSearch
from lecturepilot.learner.user_memory import UserMemoryStore
from lecturepilot.llm.usage_quota import UsageQuota
from lecturepilot.courses.youtube_discovery import YoutubeDiscovery


COURSE_TENANT_ID = "tenant-tuebingen"
load_project_env()


def create_app() -> FastAPI:
    SessionAuthSettings.from_env()
    configure_metadata_file_logging()
    release = release_info()
    app = FastAPI(
        title="LecturePilot API",
        version=release.version,
        lifespan=migrate_storage_on_startup,
        **production_fastapi_kwargs(),
    )

    register_exception_handlers(app)

    app.state.database = Database()
    app.state.runtime_readiness = RuntimeReadiness(app.state.database)
    app.state.session_store = SessionStore(app.state.database)
    app.state.usage_quota = UsageQuota(app.state.database)
    app.state.course_tenant_id = COURSE_TENANT_ID
    app.state.model_usage = ModelUsageRecorder(app.state.database, tenant_id=COURSE_TENANT_ID)
    app.state.professor_usage = ProfessorUsageRepository(app.state.database)
    app.state.observability = observability_from_env()
    app.state.university_course_search = AlmaUniversityCourseSearch()
    app.state.agent_harness = LecturePilotHarness(
        model_client=NativeModelClient(app.state.model_usage)
    )
    app.state.course_planner = CourseCanvasAuthor(app.state.model_usage)
    app.state.lecture_schedule_planner = LectureSchedulePlanner(
        model_client=NativeScheduleClient(app.state.model_usage)
    )
    app.state.source_routing_planner = CourseSourceRoutingPlanner(
        model_client=NativeSourceRoutingClient(app.state.model_usage)
    )
    app.state.practice_design_planner = PracticeDesignPlanner(
        usage_recorder=app.state.model_usage,
        review_client=NativePracticeDesignReviewClient(app.state.model_usage),
    )
    app.state.open_answer_evaluator = OpenAnswerEvaluator(
        model_client=NativeOpenAnswerEvaluationClient(app.state.model_usage)
    )
    app.state.canvas_workspace = CanvasWorkspace()
    app.state.learner_state = LearnerStateStore(app.state.canvas_workspace.layout)
    app.state.user_memory_store = UserMemoryStore(app.state.canvas_workspace.layout)
    app.state.analytics_store = AnalyticsStore(app.state.canvas_workspace.layout)
    app.state.practice_exam_store = PracticeExamStore(app.state.canvas_workspace.layout)
    app.state.practice_exam_pdf_service = PracticeExamPdfService(app.state.practice_exam_store)
    app.state.practice_exam_generation_store = PracticeExamGenerationStore(
        app.state.canvas_workspace.layout, lease_seconds=180
    )
    app.state.practice_exam_planner = PracticeExamPlanner(
        model_client=NativePracticeExamClient(app.state.model_usage)
    )
    app.state.image_generator = image_generator_from_env()
    app.state.youtube_discovery = YoutubeDiscovery.from_env()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts())
    app.add_middleware(RequestBodyLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(CsrfProtectionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(allowed_origins()),
        allow_credentials=True,
        allow_methods=["GET", "HEAD", "OPTIONS", "POST", "PUT", "DELETE"],
        allow_headers=[
            "Accept",
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "Prefer",
            CLIENT_CONTRACT_HEADER,
            "X-Course-Ids",
            "X-CSRF-Token",
            "X-LecturePilot-Learner-Preview",
            "X-Tenant-Id",
            "X-User-Id",
            "X-User-Role",
        ],
        expose_headers=[
            CLIENT_CONTRACT_HEADER,
            "X-Generation-Id",
            "X-Generation-Repairable",
            "X-Generation-Status",
            "X-Generation-Error-Code",
            "Retry-After",
            "X-Request-ID",
        ],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestDiagnosticsMiddleware)
    app.add_middleware(SessionCookieRefreshMiddleware)

    @app.get("/health")
    async def health(response: Response) -> dict[str, str]:
        expected_commit = (os.getenv("LECTUREPILOT_COMMIT_SHA") or "").strip().lower()
        identity_matches = not expected_commit or expected_commit == release.commit_sha
        if not identity_matches:
            response.status_code = 503
        return {
            "status": "ok" if identity_matches else "error",
            "version": release.version,
            "commit_sha": release.commit_sha,
        }

    @app.get("/ready")
    def ready(response: Response) -> dict[str, object]:
        result = app.state.runtime_readiness.check()
        if not result.ready:
            response.status_code = 503
            emit_metadata_event(
                "runtime.readiness_failed",
                error=True,
                reason=result.failed_checks,
                status="error",
            )
        return {
            "status": "ok" if result.ready else "error",
            "checks": result.checks,
        }

    register_auth_routes(app, course_tenant_id=COURSE_TENANT_ID)
    register_university_course_routes(app, course_tenant_id=COURSE_TENANT_ID)
    register_account_admin_routes(app)
    register_course_support_routes(app)
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
    register_attendance_routes(app, **seeded_route_args)
    register_analytics_routes(app, **seeded_route_args)
    register_learner_lesson_state_routes(app, **seeded_route_args)
    register_canvas_annotation_routes(app, **seeded_route_args)
    register_canvas_prediction_routes(app, **seeded_route_args)
    register_review_queue_routes(app, **seeded_route_args)
    register_learner_study_routes(app, **seeded_route_args)
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
    register_course_invite_routes(app, course_tenant_id=COURSE_TENANT_ID)
    register_lecture_access_routes(
        app,
        course_tenant_id=COURSE_TENANT_ID,
        seeded_course=COURSE,
    )
    register_course_update_routes(
        app,
        course_tenant_id=COURSE_TENANT_ID,
        source_document=lambda course_id, lecture_id: course_builder_source_document(
            app, course_id, lecture_id
        ),
    )
    register_course_source_routing_routes(app, course_tenant_id=COURSE_TENANT_ID)
    register_exam_readiness_routes(
        app,
        course_tenant_id=COURSE_TENANT_ID,
        seeded_course=COURSE,
        lectures=LECTURES,
    )
    register_practice_exam_routes(app, **seeded_route_args)
    register_practice_exam_solution_routes(app, **seeded_route_args)
    register_practice_exam_attempt_routes(app, **seeded_route_args)
    register_asset_routes(app, **seeded_route_args)
    register_course_routes(
        app,
        course_tenant_id=COURSE_TENANT_ID,
        seeded_course=COURSE,
        seeded_lectures=LECTURES,
    )

    return app


app = create_app()
