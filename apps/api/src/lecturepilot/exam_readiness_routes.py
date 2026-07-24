from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import ValidationError

from lecturepilot.api_auth import request_context
from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.course_access import (
    course_actor_access,
    require_course_id_access,
    resolve_course_lectures,
)
from lecturepilot.exam_readiness import (
    ExamReadinessCheck,
    ExamReadinessPublicCheck,
    build_exam_readiness_check,
    public_exam_readiness_check,
)
from lecturepilot.exam_answer_evaluation import OpenAnswerEvaluationInput
from lecturepilot.exam_revision_plan import (
    ExamReadinessAttemptInput,
    ExamReadinessAttemptResult,
    build_exam_revision_plan,
    validate_exam_readiness_answers,
)
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.models import Course, Lecture
from lecturepilot.lecture_access_policy import can_consume_lecture
from lecturepilot.readiness_progress import ReadinessProgressStore
from lecturepilot.professor_preview import resolve_learner_workspace_access
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.tenancy import TenantContext


def register_exam_readiness_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    seeded_course: Course,
    lectures: list[Lecture],
) -> None:
    @app.get("/courses/{course_id}/exam-readiness", response_model=ExamReadinessPublicCheck)
    def exam_readiness_check(
        course_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> ExamReadinessPublicCheck:
        resolve_learner_workspace_access(
            request,
            context,
            course_id=course_id,
            course_tenant_id=course_tenant_id,
        )
        require_course_id_access(
            app,
            context,
            course_id=course_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=lectures,
        )
        check = _readiness_check(app, course_id, seeded_course, lectures, context)
        return public_exam_readiness_check(check)

    @app.post(
        "/courses/{course_id}/exam-readiness/attempts", response_model=ExamReadinessAttemptResult
    )
    async def record_exam_readiness_attempt(
        course_id: str,
        attempt: ExamReadinessAttemptInput,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> ExamReadinessAttemptResult:
        access = resolve_learner_workspace_access(
            request,
            context,
            course_id=course_id,
            course_tenant_id=course_tenant_id,
        )
        require_course_id_access(
            app,
            context,
            course_id=course_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=lectures,
        )
        check = _readiness_check(app, course_id, seeded_course, lectures, context)
        store = _progress_store(app)
        try:
            answers_by_question = validate_exam_readiness_answers(
                check=check, answers=attempt.answers
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        items = [
            OpenAnswerEvaluationInput(
                question_id=question.id,
                prompt=question.prompt,
                answer=answers_by_question[question.id].text or "",
                rubric=question.rubric,
            )
            for question in check.questions
            if question.kind == "open_ended"
        ]
        try:
            with model_usage_scope(
                actor_user_id=access.user_id,
                course_id=course_id,
                workload="readiness_evaluation",
            ):
                evaluations = await app.state.open_answer_evaluator.evaluate(items=items)
        except (ModelExecutionError, ProviderConfigurationError, ValidationError) as exc:
            raise HTTPException(
                status_code=503,
                detail="Open-answer evaluation is temporarily unavailable. Please retry.",
            ) from exc
        try:
            result = build_exam_revision_plan(
                check=check,
                answers=attempt.answers,
                open_evaluations={evaluation.question_id: evaluation for evaluation in evaluations},
                previous_attempts=store.attempt_count(user_id=access.user_id, course_id=course_id),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return store.record_attempt(user_id=access.user_id, course_id=course_id, result=result)


def _readiness_check(
    app: FastAPI,
    course_id: str,
    seeded_course: Course,
    lectures: list[Lecture],
    context: TenantContext,
) -> ExamReadinessCheck:
    course, course_lectures = resolve_course_lectures(
        app,
        course_id=course_id,
        seeded_course=seeded_course,
        seeded_lectures=lectures,
    )
    actor = course_actor_access(app, context, course_id, app.state.course_tenant_id)
    course_lectures = [
        lecture
        for lecture in course_lectures
        if can_consume_lecture(course, lecture, **actor.__dict__)
    ]
    documents = []
    for lecture in course_lectures:
        if not app.state.canvas_workspace.has_published_course_canvas(
            course_id=course_id,
            lecture_id=lecture.id,
        ):
            continue
        try:
            document = app.state.canvas_workspace.course_canvas_store.read(
                course_id=course_id,
                lecture_id=lecture.id,
                workspace_path=f"exam-readiness/{lecture.id}/index.md",
            )
        except CanvasWorkspaceError:
            continue
        if document is not None:
            documents.append(document)
    if not documents:
        raise HTTPException(
            status_code=404,
            detail="Publish at least one lecture canvas before running the exam readiness check.",
        )
    check = build_exam_readiness_check(
        course_id=course_id,
        documents=documents,
        lectures=course_lectures,
    )
    if not check.questions:
        raise HTTPException(
            status_code=422,
            detail="Published canvases do not contain enough quiz or section content for an exam readiness check.",
        )
    return check


def _progress_store(app: FastAPI) -> ReadinessProgressStore:
    return ReadinessProgressStore(app.state.canvas_workspace.layout)
