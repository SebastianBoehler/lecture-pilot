from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.analytics import LectureAnalyticsSummary, QuizAnswerInput, QuizAnswerResult
from lecturepilot.agent_state_access import analytics_store, learner_state_store
from lecturepilot.api_auth import (
    request_context,
    require_course_manager,
)
from lecturepilot.audit import record_audit_event
from lecturepilot.analytics_quiz_submission import quiz_block, quiz_feedback
from lecturepilot.course_access import require_lecture_id_access
from lecturepilot.course_canvas_context import (
    AnalyticsPublicationContext,
    InvalidPublishedCanvasContextError,
)
from lecturepilot.course_analytics import (
    CourseAnalyticsSummary,
    CurrentLectureAnalyticsContract,
    course_analytics_summary,
)
from lecturepilot.course_schedule_store import read_course_workspace
from lecturepilot.models import Course, Lecture
from lecturepilot.readiness_analytics import CourseReadinessSummary, course_readiness_summary
from lecturepilot.readiness_progress import ReadinessProgressStore
from lecturepilot.professor_preview import resolve_learner_workspace_access
from lecturepilot.quiz_identity import canonical_quiz_id
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
        try:
            snapshot = app.state.canvas_workspace.course_canvas_store.read_published_snapshot(
                course_id=course_id,
                lecture_id=lecture_id,
            )
        except InvalidPublishedCanvasContextError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if snapshot is None:
            raise HTTPException(status_code=404, detail="Canvas has not been published.")
        overlay_sections = app.state.canvas_workspace.read_learner_overlay_sections(
            course_id=course_id,
            lecture_id=lecture_id,
            user_id=access.user_id,
        )
        document = snapshot.document.model_copy(
            update={"sections": [*snapshot.document.sections, *overlay_sections]}
        )
        block = quiz_block(document, answer.block_id)
        quiz_id = canonical_quiz_id(block)
        if answer.option_index >= len(block.items):
            raise HTTPException(status_code=400, detail="Quiz option does not exist.")
        correct = (
            answer.option_index == block.answer_index
            if isinstance(block.answer_index, int)
            else None
        )
        try:
            state, _ = learner_state_store(app).record_quiz_answer(
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
        analytics_store(app).record_quiz_answer(
            course_id=course_id,
            lecture_id=lecture_id,
            user_id=access.user_id,
            attendance=answer.attendance,
            block=block,
            option_index=state.selected_index,
            publication_version=snapshot.version,
            learning_map_revision=snapshot.learning_map_revision,
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
            feedback=quiz_feedback(state.correct),
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
        store = analytics_store(app)
        current_contracts = {}
        for lecture_id in lecture_ids:
            analytics_context = _analytics_context(app, course_id, lecture_id)
            learning_map = analytics_context.learning_map
            current_contracts[lecture_id] = CurrentLectureAnalyticsContract(
                publication_version=analytics_context.publication_version,
                learning_map_revision=analytics_context.learning_map_revision,
                gate_revisions={gate.id: gate.revision for gate in learning_map.gates},
            )
        summary = course_analytics_summary(
            course_id=course_id,
            lecture_ids=lecture_ids,
            read_events=lambda lecture_id: store.iter_events(
                course_id=course_id,
                lecture_id=lecture_id,
            ),
            current_contracts=current_contracts,
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
        analytics_context = _analytics_context(app, course_id, lecture_id)
        learning_map = analytics_context.learning_map
        summary = analytics_store(app).summary(
            course_id=course_id,
            lecture_id=lecture_id,
            current_publication_version=analytics_context.publication_version,
            current_gate_revisions={gate.id: gate.revision for gate in learning_map.gates},
            current_learning_map_revision=analytics_context.learning_map_revision,
        )
        record_audit_event(
            app.state.database,
            context,
            event_type="analytics.aggregate_viewed",
            target_type="lecture",
            target_id=f"{course_id}:{lecture_id}",
        )
        return summary.model_copy(update={"learning_map": learning_map})

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


def _analytics_context(
    app: FastAPI, course_id: str, lecture_id: str
) -> AnalyticsPublicationContext:
    try:
        return app.state.canvas_workspace.course_canvas_store.read_analytics_context(
            course_id=course_id,
            lecture_id=lecture_id,
        )
    except InvalidPublishedCanvasContextError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
