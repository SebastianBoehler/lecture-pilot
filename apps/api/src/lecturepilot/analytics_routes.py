from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.analytics import (
    AnalyticsStore,
    LectureAnalyticsSummary,
    QuizAnswerInput,
    QuizAnswerResult,
)
from lecturepilot.agent_state_access import learner_state_store
from lecturepilot.api_auth import (
    request_context,
    require_course_manager,
)
from lecturepilot.audit import record_audit_event
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument
from lecturepilot.course_access import require_lecture_id_access
from lecturepilot.course_analytics import CourseAnalyticsSummary, course_analytics_summary
from lecturepilot.course_schedule_store import read_course_workspace
from lecturepilot.learning_map import LearningMap, write_learning_map
from lecturepilot.models import Course, Lecture
from lecturepilot.readiness_analytics import CourseReadinessSummary, course_readiness_summary
from lecturepilot.readiness_progress import ReadinessProgressStore
from lecturepilot.professor_preview import resolve_learner_workspace_access
from lecturepilot.quiz_identity import (
    DuplicateCanonicalQuizIdError,
    canonical_quiz_id,
    is_quiz_block,
    validate_unique_quiz_ids,
)
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
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> QuizAnswerResult:
        access = resolve_learner_workspace_access(
            request,
            context,
            course_id=course_id,
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
        snapshot = app.state.canvas_workspace.course_canvas_store.read_published_snapshot(
            course_id=course_id,
            lecture_id=lecture_id,
        )
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Canvas has not been published.")
        block = _quiz_block(snapshot.document, answer.block_id)
        quiz_id = canonical_quiz_id(block)
        if answer.option_index >= len(block.items):
            raise HTTPException(status_code=400, detail="Quiz option does not exist.")
        correct = (
            answer.option_index == block.answer_index
            if isinstance(block.answer_index, int)
            else None
        )
        try:
            state, created = learner_state_store(app).record_quiz_answer(
                course_id=course_id,
                lecture_id=lecture_id,
                user_id=access.user_id,
                quiz_id=quiz_id,
                publication_version=snapshot.version,
                attempt_id=answer.attempt_id,
                selected_index=answer.option_index,
                correct=correct,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if created:
            _analytics_store(app).record_quiz_answer(
                course_id=course_id,
                lecture_id=lecture_id,
                user_id=access.user_id,
                attendance=answer.attendance,
                block=block,
                option_index=answer.option_index,
                attempt_index=state.attempt_index,
                first_attempt_correct=state.first_attempt_correct,
                correction_state=state.correction_state,
            )
        return QuizAnswerResult(
            block_id=quiz_id,
            component_id=quiz_id,
            selected_index=state.selected_index,
            correct=state.correct,
            publication_version=state.publication_version,
            attempt_index=state.attempt_index,
            first_attempt_correct=state.first_attempt_correct,
            latest_outcome=state.latest_outcome,
            correction_state=state.correction_state,
            feedback=_quiz_feedback(state.correct),
        )

    @app.get(
        "/admin/courses/{course_id}/analytics",
        response_model=CourseAnalyticsSummary,
    )
    def course_analytics(
        course_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CourseAnalyticsSummary:
        require_course_manager(
            context,
            course_tenant_id=course_tenant_id,
            request=request,
            course_id=course_id,
        )
        workspace = read_course_workspace(
            app.state.canvas_workspace.course_media_root(course_id),
            course_id,
        )
        if workspace is None:
            raise HTTPException(status_code=404, detail="Course workspace not found.")
        lecture_ids = [
            lecture.id
            for lecture in workspace.lectures
            if app.state.canvas_workspace.has_published_course_canvas(
                course_id=course_id,
                lecture_id=lecture.id,
            )
        ]
        store = _analytics_store(app)
        summary = course_analytics_summary(
            course_id=course_id,
            lecture_ids=lecture_ids,
            read_events=lambda lecture_id: store.iter_events(
                course_id=course_id,
                lecture_id=lecture_id,
            ),
        )
        record_audit_event(
            app.state.database,
            context,
            event_type="analytics.course_aggregate_viewed",
            target_type="course",
            target_id=course_id,
        )
        return summary

    @app.get(
        "/admin/courses/{course_id}/lectures/{lecture_id}/analytics",
        response_model=LectureAnalyticsSummary,
    )
    def lecture_analytics(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> LectureAnalyticsSummary:
        require_course_manager(
            context,
            course_tenant_id=course_tenant_id,
            request=request,
            course_id=course_id,
        )
        summary = _analytics_store(app).summary(course_id=course_id, lecture_id=lecture_id)
        record_audit_event(
            app.state.database,
            context,
            event_type="analytics.aggregate_viewed",
            target_type="lecture",
            target_id=f"{course_id}:{lecture_id}",
        )
        return summary.model_copy(
            update={"learning_map": _learning_map(app, course_id, lecture_id)}
        )

    @app.get(
        "/admin/courses/{course_id}/exam-readiness/summary",
        response_model=CourseReadinessSummary,
    )
    def readiness_summary(
        course_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> CourseReadinessSummary:
        require_course_manager(
            context,
            course_tenant_id=course_tenant_id,
            request=request,
            course_id=course_id,
        )
        summary = course_readiness_summary(
            course_id=course_id,
            store=ReadinessProgressStore(app.state.canvas_workspace.layout),
        )
        record_audit_event(
            app.state.database,
            context,
            event_type="readiness.aggregate_viewed",
            target_type="course",
            target_id=course_id,
        )
        return summary


def _quiz_block(document: CanvasDocument, block_id: str) -> CanvasBlock:
    try:
        validate_unique_quiz_ids(document)
    except DuplicateCanonicalQuizIdError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Published canvas has duplicate quiz ID '{exc.quiz_id}'.",
        ) from exc
    matches = [
        block
        for section in document.sections
        for block in section.blocks
        if canonical_quiz_id(block) == block_id
    ]
    quizzes = [block for block in matches if is_quiz_block(block)]
    if quizzes:
        return quizzes[0]
    if matches:
        raise HTTPException(status_code=400, detail="Canvas block is not a quiz component.")
    raise HTTPException(status_code=404, detail="Quiz block not found.")


def _analytics_store(app: FastAPI) -> AnalyticsStore:
    store = app.state.analytics_store
    layout = getattr(app.state.canvas_workspace, "layout", None)
    if layout is not None and store.layout is not layout:
        store = AnalyticsStore(layout)
        app.state.analytics_store = store
    return store


def _quiz_feedback(correct: bool | None) -> str:
    if correct is True:
        return "Correct. Explain why this option fits the concept before moving on."
    if correct is False:
        return (
            "Review the explanation above, explain why your choice does not fit, "
            "then try a correction."
        )
    return "Your answer was stored. Discuss the reasoning with the tutor."


def _learning_map(app: FastAPI, course_id: str, lecture_id: str) -> LearningMap | None:
    if not app.state.canvas_workspace.has_published_course_canvas(
        course_id=course_id,
        lecture_id=lecture_id,
    ):
        return None
    canvas_dir = app.state.canvas_workspace.course_canvas_store.path(course_id, lecture_id)
    document = app.state.canvas_workspace.course_canvas_store.read(
        course_id=course_id,
        lecture_id=lecture_id,
        workspace_path=str(canvas_dir / "index.md"),
    )
    return write_learning_map(document, canvas_dir) if document else None
