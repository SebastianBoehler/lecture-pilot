"""A professor change request as one owned canvas-generation job.

Runs inside the ordinary generation job store, so `lecture-states` reports it as `generating`
and then `ready` or a failure. The result is persisted as a normal draft for the current
approved goals and sources; review and Approve & publish stay unchanged.
"""

from collections.abc import Callable
from functools import partial

from anyio import to_thread
from fastapi import FastAPI

from lecturepilot.authoring import course_canvas_generation_ownership as ownership_store
from lecturepilot.authoring.authoring_generation_scope import generation_authoring_scope
from lecturepilot.authoring.authoring_runtime import authoring_scope
from lecturepilot.authoring.canvas_change_authoring import CanvasChangeRequestError
from lecturepilot.authoring.canvas_change_base import change_request_base
from lecturepilot.authoring.canvas_change_models import (
    CanvasChangeInput,
    change_record,
    write_change_record,
)
from lecturepilot.authoring.canvas_change_splice import restore_unchanged
from lecturepilot.authoring.course_canvas_generation import canvas_language, run_source_prep
from lecturepilot.authoring.course_canvas_generation_persistence import write_current_draft
from lecturepilot.canvas.canvas_models import CanvasDocument
from lecturepilot.core.logging_observability import operation_scope
from lecturepilot.courses.course_media import apply_course_media, course_media_evidence
from lecturepilot.identity.tenancy import TenantContext
from lecturepilot.llm.model_usage import model_usage_scope


async def generate_canvas_change(
    app: FastAPI,
    *,
    course_id: str,
    lecture_id: str,
    context: TenantContext,
    source_document: Callable[[str, str], CanvasDocument],
    change: CanvasChangeInput,
    generation_id: str,
    attempt: int,
) -> CanvasDocument:
    layout = app.state.canvas_workspace.layout
    media_root = app.state.canvas_workspace.course_media_root(course_id)
    with operation_scope(generation_id):
        source, source_revision, design, ownership = await run_source_prep(
            partial(
                ownership_store.begin_owned_generation_source,
                layout,
                media_root,
                source_document,
                course_id=course_id,
                lecture_id=lecture_id,
                generation_id=generation_id,
                attempt=attempt,
            )
        )
        base = await to_thread.run_sync(
            partial(
                change_request_base,
                layout,
                course_id=course_id,
                lecture_id=lecture_id,
                allow_running=True,
            )
        )
        if base.design.revision != design.revision:
            raise CanvasChangeRequestError(
                "The approved learning goals changed. Reload the course page and try again."
            )
        source = course_media_evidence(source, media_root)
        with (
            model_usage_scope(
                actor_user_id=context.user_id, course_id=course_id, workload="course_canvas"
            ),
            authoring_scope(
                generation_authoring_scope(
                    app, ownership=ownership, source_revision=source_revision
                )
            ),
        ):
            result = await app.state.course_planner.change_canvas(
                source,
                practice_design=design,
                base=base.document,
                instruction=change.instruction,
                section_ids=change.named_sections(),
                output_language=canvas_language(app, course_id),
            )
        document = restore_unchanged(
            base.document,
            apply_course_media(result.document, media_root),
            set(result.section_ids),
        )
        document = await to_thread.run_sync(
            partial(
                write_current_draft,
                app,
                document,
                expected_source_revision=source_revision,
                ownership=ownership,
            )
        )
        record = change_record(
            generation_id=generation_id,
            base=base.kind,
            instruction=change.instruction,
            section_ids=list(result.section_ids),
            selection=result.selection,
            reasons=result.reasons,
        )
        await to_thread.run_sync(
            partial(
                write_change_record,
                layout,
                course_id=course_id,
                lecture_id=lecture_id,
                record=record,
            )
        )
        return document
