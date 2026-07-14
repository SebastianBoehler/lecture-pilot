from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_media import apply_course_media, course_media_evidence
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
) -> CanvasDocument:
    generation_id = uuid4().hex
    observability = app.state.observability
    common = {
        "course_id": course_id,
        "lecture_id": lecture_id,
        "generation_id": generation_id,
        "attempt": 1,
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
            source = await run_in_threadpool(source_document, course_id, lecture_id)
        with observability.tool_span("course_canvas_generation", stage="source_media", **common):
            media_root = app.state.canvas_workspace.course_media_root(course_id)
            source = course_media_evidence(source, media_root)
        with observability.tool_span("course_canvas_generation", stage="model_plan", **common):
            with model_usage_scope(
                actor_user_id=context.user_id,
                course_id=course_id,
                workload="course_canvas",
            ):
                document = await app.state.course_planner.plan_canvas(source)
        with observability.tool_span("course_canvas_generation", stage="output_media", **common):
            document = apply_course_media(document, media_root)
        with observability.tool_span("course_canvas_generation", stage="draft_persist", **common):
            document = app.state.canvas_workspace.write_course_canvas_draft(document)
        generation_span.set_outputs(
            {"section_count": len(document.sections), "warning_count": len(document.warnings)}
        )
        return document
