from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from lecturepilot.analytics import (
    AnalyticsStore,
    LectureAnalyticsSummary,
    QuizAnswerInput,
    QuizAnswerResult,
)
from lecturepilot.api_auth import (
    request_context,
    require_course_manager,
    require_learner_workspace_access,
)
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument
from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.course_access import require_lecture_id_access
from lecturepilot.models import Course, Lecture
from lecturepilot.readiness_analytics import CourseReadinessSummary, course_readiness_summary
from lecturepilot.readiness_progress import ReadinessProgressStore
from lecturepilot.tenancy import TenantContext


def register_analytics_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> None:
    @app.post(
        "/courses/{course_id}/lectures/{lecture_id}/analytics/quiz-answer",
        response_model=QuizAnswerResult,
    )
    def record_quiz_answer(
        course_id: str,
        lecture_id: str,
        answer: QuizAnswerInput,
        context: TenantContext = Depends(request_context),
    ) -> QuizAnswerResult:
        require_learner_workspace_access(
            context,
            learner_user_id=answer.user_id,
            course_tenant_id=course_tenant_id,
        )
        require_lecture_id_access(
            app,
            context,
            course_id=course_id,
            lecture_id=lecture_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=seeded_lectures,
        )
        if not app.state.canvas_workspace.has_published_course_canvas(
            course_id=course_id,
            lecture_id=lecture_id,
        ):
            raise HTTPException(status_code=404, detail="Canvas has not been published.")
        try:
            document = app.state.canvas_workspace.read_document(
                course_id=course_id,
                lecture_id=lecture_id,
                user_id=answer.user_id,
            )
        except CanvasWorkspaceError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        block = _quiz_block(document, answer.block_id)
        if answer.option_index >= len(block.items):
            raise HTTPException(status_code=400, detail="Quiz option does not exist.")
        return _analytics_store(app).record_quiz_answer(
            course_id=course_id,
            lecture_id=lecture_id,
            user_id=answer.user_id,
            attendance=answer.attendance,
            block=block,
            option_index=answer.option_index,
        )

    @app.get(
        "/admin/courses/{course_id}/lectures/{lecture_id}/analytics",
        response_model=LectureAnalyticsSummary,
    )
    def lecture_analytics(
        course_id: str,
        lecture_id: str,
        context: TenantContext = Depends(request_context),
    ) -> LectureAnalyticsSummary:
        require_course_manager(context, course_tenant_id=course_tenant_id)
        return _analytics_store(app).summary(course_id=course_id, lecture_id=lecture_id)

    @app.get(
        "/admin/courses/{course_id}/exam-readiness/summary",
        response_model=CourseReadinessSummary,
    )
    def readiness_summary(
        course_id: str,
        context: TenantContext = Depends(request_context),
    ) -> CourseReadinessSummary:
        require_course_manager(context, course_tenant_id=course_tenant_id)
        return course_readiness_summary(
            course_id=course_id,
            store=ReadinessProgressStore(app.state.canvas_workspace.layout),
        )


def _quiz_block(document: CanvasDocument, block_id: str) -> CanvasBlock:
    for section in document.sections:
        for block in section.blocks:
            if block.id != block_id:
                continue
            if block.type not in {"quiz", "component"}:
                raise HTTPException(status_code=400, detail="Canvas block is not a quiz component.")
            return block
    raise HTTPException(status_code=404, detail="Quiz block not found.")


def _analytics_store(app: FastAPI) -> AnalyticsStore:
    store = app.state.analytics_store
    layout = getattr(app.state.canvas_workspace, "layout", None)
    if layout is not None and store.layout is not layout:
        store = AnalyticsStore(layout)
        app.state.analytics_store = store
    return store
