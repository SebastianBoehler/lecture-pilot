from __future__ import annotations

from fastapi import FastAPI, HTTPException

from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.course_access import lecture_views_for_context, resolve_course_lectures
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.models import Course, Lecture
from lecturepilot.practice_exam_models import PracticeExam, PracticeExamGenerationInput
from lecturepilot.practice_exam_prompt import MAX_PPI_EVIDENCE_CHARS
from lecturepilot.tenancy import TenantContext


async def generate_practice_exam(
    app: FastAPI,
    *,
    context: TenantContext,
    course_id: str,
    input_data: PracticeExamGenerationInput,
    seeded_course: Course,
    seeded_lectures: list[Lecture],
) -> PracticeExam:
    course, lectures = resolve_course_lectures(
        app,
        course_id=course_id,
        seeded_course=seeded_course,
        seeded_lectures=seeded_lectures,
    )
    views = lecture_views_for_context(
        app,
        context,
        course,
        lectures,
        course_tenant_id=app.state.course_tenant_id,
    )
    documents = []
    for view in views:
        if not view.unlocked or not view.content_ready:
            continue
        try:
            document = app.state.canvas_workspace.course_canvas_store.read(
                course_id=course_id,
                lecture_id=view.lecture.id,
                workspace_path=f"practice-exams/{view.lecture.id}/index.md",
            )
        except CanvasWorkspaceError:
            continue
        if document is not None:
            documents.append(document)
    if not documents:
        raise HTTPException(
            status_code=404,
            detail="Publish and unlock at least one lecture canvas before generating an exam.",
        )
    ppi_sources: dict[str, list[str]] = {}
    ppi_excerpt_limit = MAX_PPI_EVIDENCE_CHARS // max(1, len(input_data.ppi_source_ids))
    for source_id in input_data.ppi_source_ids:
        try:
            ppi_sources[source_id] = [
                text
                for _path, text in app.state.ppi_exam_source_store.normalized_text(
                    user_id=context.user_id,
                    course_id=course_id,
                    source_id=source_id,
                    max_characters=ppi_excerpt_limit,
                )
            ]
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=404, detail="Selected PPI source was not found."
            ) from exc
    with model_usage_scope(
        actor_user_id=context.user_id,
        course_id=course_id,
        workload="practice_exam_generation",
    ):
        return await app.state.practice_exam_planner.plan(
            course_id=course_id,
            course_title=course.title,
            language=course.canvas_language,
            duration_minutes=input_data.duration_minutes,
            question_count=input_data.question_count,
            documents=documents,
            ppi_sources=ppi_sources,
        )
