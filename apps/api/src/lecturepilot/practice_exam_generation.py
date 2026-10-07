from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException

from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.practice_exam_focus import practice_exam_goal_focus, bounded_exam_goal_focus
from lecturepilot.course_access import lecture_views_for_context, resolve_course_lectures
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.practice_exam_limits import (
    EXAM_RESERVED_TOKENS,
    EXAM_DEADLINE_SECONDS,
    practice_exam_budget,
)
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.model_usage_total import model_usage_total
from lecturepilot.usage_quota import UsageQuotaExceeded
from lecturepilot.models import Course, Lecture
from lecturepilot.practice_exam_models import PracticeExam, PracticeExamGenerationInput
from lecturepilot.practice_exam_prompt import MAX_PPI_EVIDENCE_CHARS, authoritative_canvas_evidence
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
    snapshots = []
    for view in views:
        if not view.unlocked or not view.content_ready:
            continue
        snapshot = app.state.canvas_workspace.course_canvas_store.read_current_published_snapshot(
            course_id=course_id,
            lecture_id=view.lecture.id,
        )
        if snapshot is not None:
            documents.append(snapshot.document)
            snapshots.append(snapshot)
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
    _, authoritative_ids = authoritative_canvas_evidence(documents)
    learner_focus = []
    progress_store = CoachingProgressStore(app.state.canvas_workspace.layout)
    for snapshot in snapshots:
        progress = await asyncio.to_thread(
            progress_store.read,
            user_id=context.user_id,
            course_id=course_id,
            lecture_id=snapshot.document.lecture_id,
        )
        learner_focus.extend(
            practice_exam_goal_focus(
                snapshot.document.lecture_id,
                snapshot.learning_map,
                progress,
                authoritative_ids,
            )
        )
    learner_focus = bounded_exam_goal_focus(learner_focus)
    scope = dict(tenant_id=context.tenant_id, user_id=context.user_id, course_id=course_id)
    reservation = EXAM_RESERVED_TOKENS
    usage_date = datetime.now(UTC).date()
    try:
        reserved = await asyncio.to_thread(
            app.state.usage_quota.reserve_turn,
            **scope,
            reserved_tokens=reservation,
            usage_date=usage_date,
        )
    except UsageQuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    with model_usage_total() as total:
        try:
            with (
                practice_exam_budget(),
                model_usage_scope(
                    actor_user_id=context.user_id,
                    course_id=course_id,
                    workload="practice_exam_generation",
                ),
            ):
                async with asyncio.timeout(EXAM_DEADLINE_SECONDS):
                    return await app.state.practice_exam_planner.plan(
                        course_id=course_id,
                        course_title=course.title,
                        language=course.canvas_language,
                        duration_minutes=input_data.duration_minutes,
                        question_count=input_data.question_count,
                        documents=documents,
                        ppi_sources=ppi_sources,
                        choice_format=input_data.choice_format,
                        learner_focus=learner_focus,
                    )
        except TimeoutError as exc:
            raise ModelExecutionError("Practice exam generation deadline exceeded.") from exc
        finally:
            if reserved:
                await asyncio.to_thread(
                    app.state.usage_quota.release_turn,
                    **scope,
                    reserved_tokens=reservation,
                    actual_tokens=total.total_tokens,
                    usage_date=usage_date,
                )
