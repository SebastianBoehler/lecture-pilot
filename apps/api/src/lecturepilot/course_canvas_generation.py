from __future__ import annotations

from hashlib import sha256

from collections.abc import Callable
from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_content_filter import filter_source_document_for_planning
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_generation_jobs import CanvasGenerationJob
from lecturepilot.course_canvas_repairs import (
    lecture_source_revision,
    matching_repair_guidance,
    persist_repair_guidance,
    resolve_source_with_revision,
)
from lecturepilot.course_canvas_store import InvalidCanvasDraftError
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.course_media import apply_course_media, course_media_evidence
from lecturepilot.course_canvas_validation import validate_planned_document
from lecturepilot.course_schedule_store import read_course_workspace
from lecturepilot.logging_observability import operation_scope
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.tenancy import TenantContext


async def generate_course_canvas_draft(
    app: FastAPI,
    *,
    course_id: str,
    lecture_id: str,
    context: TenantContext,
    source_document: Callable[[str, str], CanvasDocument],
    generation_id: str,
    attempt: int,
    repair_failure_code: str | None = None,
    repair_failure_detail: str | None = None,
) -> CanvasDocument:
    observability = app.state.observability
    common = {
        "course_id": course_id,
        "lecture_id": lecture_id,
        "generation_id": generation_id,
        "attempt": attempt,
    }
    registry = getattr(getattr(app.state, "course_planner", None), "provider_registry", None)
    model = getattr(registry, "model", None)
    if isinstance(model, str) and model:
        common["model"] = model
        common["provider"] = model.partition("/")[0].lower()
    with (
        operation_scope(generation_id),
        observability.tool_span(
            "course_canvas_generation",
            stage="request",
            workload="course_canvas",
            **common,
        ) as generation_span,
    ):
        with observability.tool_span("course_canvas_generation", stage="source_resolve", **common):
            source, source_revision = await run_in_threadpool(
                resolve_source_with_revision,
                app.state.canvas_workspace.layout,
                app.state.canvas_workspace.course_media_root(course_id),
                source_document,
                course_id,
                lecture_id,
            )
            if source_revision is None:
                raise InvalidCanvasDraftError("Draft source provenance is unavailable.")
        with observability.tool_span("course_canvas_generation", stage="source_media", **common):
            media_root = app.state.canvas_workspace.course_media_root(course_id)
            source = course_media_evidence(source, media_root)
        repair_record = matching_repair_guidance(
            app.state.canvas_workspace.layout,
            course_id=course_id,
            lecture_id=lecture_id,
        )
        repair_context = repair_failure_detail or (
            repair_record.failure_detail if repair_record else None
        )
        output_language = _canvas_language(app, course_id)
        with observability.tool_span("course_canvas_generation", stage="model_plan", **common):
            with model_usage_scope(
                actor_user_id=context.user_id,
                course_id=course_id,
                workload="course_canvas",
            ):
                try:
                    if repair_context:
                        document = await app.state.course_planner.plan_canvas(
                            source,
                            repair_context=repair_context,
                            output_language=output_language,
                        )
                    else:
                        document = await app.state.course_planner.plan_canvas(
                            source,
                            output_language=output_language,
                        )
                except CanvasGenerationRepairableError as exc:
                    raise exc.with_source_revision(
                        lecture_source_revision(
                            app.state.canvas_workspace.layout,
                            course_id=course_id,
                            lecture_id=lecture_id,
                        )
                    )
        with observability.tool_span("course_canvas_generation", stage="output_media", **common):
            document = apply_course_media(document, media_root)
        with observability.tool_span("course_canvas_generation", stage="draft_persist", **common):
            document = _write_current_draft(
                app,
                document,
                expected_source_revision=source_revision,
            )
        if repair_failure_code and repair_failure_detail:
            persist_repair_guidance(
                app.state.canvas_workspace.layout,
                course_id=course_id,
                lecture_id=lecture_id,
                failure_code=repair_failure_code,
                failure_detail=repair_failure_detail,
                generation_id=generation_id,
            )
        generation_span.set_outputs(
            {"section_count": len(document.sections), "warning_count": len(document.warnings)}
        )
        return document


async def repair_targeted_course_canvas_draft(
    app: FastAPI,
    *,
    course_id: str,
    lecture_id: str,
    context: TenantContext,
    source_document: Callable[[str, str], CanvasDocument],
    failure: CanvasGenerationJob,
    generation_id: str,
    attempt: int,
) -> CanvasDocument:
    repair = failure.repair
    if repair is None or failure.error_detail is None:
        raise CanvasGenerationRepairableError("No targeted repair candidate is available.")
    candidate = repair.candidate
    common = {
        "course_id": course_id,
        "lecture_id": lecture_id,
        "generation_id": generation_id,
        "attempt": attempt,
        "repair_section_id": repair.section_id,
        "repair_block_id": repair.block_id or "",
    }
    observability = app.state.observability
    with (
        operation_scope(generation_id),
        observability.tool_span(
            "course_canvas_generation",
            stage="targeted_repair",
            workload="course_canvas",
            **common,
        ) as repair_span,
    ):
        source, source_revision = await run_in_threadpool(
            resolve_source_with_revision,
            app.state.canvas_workspace.layout,
            app.state.canvas_workspace.course_media_root(course_id),
            source_document,
            course_id,
            lecture_id,
        )
        if source_revision is None:
            raise InvalidCanvasDraftError("Draft source provenance is unavailable.")
        media_root = app.state.canvas_workspace.course_media_root(course_id)
        source = course_media_evidence(source, media_root)
        source = filter_source_document_for_planning(source)
        output_language = _canvas_language(app, course_id)
        try:
            with model_usage_scope(
                actor_user_id=context.user_id,
                course_id=course_id,
                workload="course_canvas",
            ):
                document = await _repair_until_quality_valid(
                    app,
                    source=source,
                    candidate=candidate,
                    section_id=repair.section_id,
                    block_id=repair.block_id,
                    failure_context=failure.error_detail,
                    output_language=output_language,
                )
        except CanvasGenerationRepairableError as exc:
            if exc.candidate is None:
                exc.with_candidate(candidate)
            raise exc.with_source_revision(repair.source_revision)
        document = apply_course_media(document, media_root)
        document = _write_current_draft(
            app,
            document,
            expected_source_revision=source_revision,
        )
        persist_repair_guidance(
            app.state.canvas_workspace.layout,
            course_id=course_id,
            lecture_id=lecture_id,
            failure_code=failure.error_code or "generation_failed",
            failure_detail=failure.error_detail,
            generation_id=generation_id,
        )
        repair_span.set_outputs(
            {"section_count": len(document.sections), "warning_count": len(document.warnings)}
        )
        return document


async def _repair_until_quality_valid(
    app: FastAPI,
    *,
    source: CanvasDocument,
    candidate: CanvasDocument,
    section_id: str,
    block_id: str | None,
    failure_context: str,
    output_language: str,
) -> CanvasDocument:
    active_candidate = candidate
    active_section_id = section_id
    active_block_id = block_id
    active_failure = failure_context
    repair_states: set[tuple[str, str | None, str]] = set()
    while True:
        candidate_digest = sha256(active_candidate.model_dump_json().encode()).hexdigest()
        repair_state = (active_section_id, active_block_id, candidate_digest)
        if repair_state in repair_states:
            raise CanvasGenerationRepairableError(
                active_failure,
                candidate=active_candidate,
                section_id=active_section_id,
                block_id=active_block_id,
            )
        repair_states.add(repair_state)
        repaired: CanvasDocument | None = None
        try:
            repaired = await app.state.course_planner.repair_section(
                source,
                active_candidate,
                section_id=active_section_id,
                block_id=active_block_id,
                failure_context=active_failure,
                output_language=output_language,
            )
            validate_planned_document(repaired, source)
            await app.state.course_planner.validate_quality(source, repaired)
            return repaired
        except CanvasGenerationRepairableError as exc:
            next_candidate = exc.candidate or repaired or active_candidate
            if exc.section_id is None:
                raise exc.with_candidate(next_candidate)
            active_candidate = next_candidate
            active_section_id = exc.section_id
            active_block_id = exc.block_id
            active_failure = str(exc)


def _canvas_language(app: FastAPI, course_id: str) -> str:
    workspace = read_course_workspace(
        app.state.canvas_workspace.course_media_root(course_id),
        course_id,
    )
    return workspace.course.canvas_language if workspace else "en"


def _write_current_draft(
    app: FastAPI,
    document: CanvasDocument,
    *,
    expected_source_revision: str,
) -> CanvasDocument:
    course_root = app.state.canvas_workspace.course_media_root(document.course_id)
    with locked_course_state(course_root):
        return app.state.canvas_workspace.write_course_canvas_draft(
            document,
            expected_source_revision=expected_source_revision,
        )
