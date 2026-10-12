from __future__ import annotations

from datetime import date

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool

from lecturepilot.document_converter_client import DocumentConverterError
from lecturepilot.durable_files import exclusive_file_lock
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.models import LectureScheduleProposal
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.source_document_normalization import normalize_selected_documents
from lecturepilot.source_index import indexed_course_files
from lecturepilot.tenancy import TenantContext


async def generate_lecture_schedule(
    app: FastAPI,
    *,
    course_id: str,
    context: TenantContext,
    first_lecture_date: date | None,
    requested_count: int | None,
) -> LectureScheduleProposal:
    roots = app.state.canvas_workspace.source_bundle_roots(
        course_id,
        include_seeded_materials=False,
    )
    layout = app.state.canvas_workspace.layout
    normalized_root = layout.course_normalized_dir(course_id)

    def prepare():  # Hashing, conversion and lock waits stay off the event loop.
        course_root = layout.course_root(course_id)
        with locked_course_state(course_root):
            files = indexed_course_files(layout=layout, course_id=course_id)
        with exclusive_file_lock(course_root / "builder" / "source-derivation"):
            normalize_selected_documents(
                files=files,
                source_root=layout.course_uploads_dir(course_id),
                normalized_root=normalized_root,
            )
        return files

    try:
        files = await run_in_threadpool(prepare)
    except DocumentConverterError as exc:
        raise ProviderConfigurationError(str(exc)) from exc
    roots = [*roots, normalized_root]
    with app.state.observability.tool_span(
        "course_schedule_generation",
        course_id=course_id,
        requested_count=requested_count,
        source_count=len(files),
        workload="course_schedule",
    ) as span:
        with model_usage_scope(
            actor_user_id=context.user_id,
            course_id=course_id,
            workload="course_schedule",
        ):
            proposal = await app.state.lecture_schedule_planner.propose_schedule(
                course_id=course_id,
                files=files,
                roots=list(roots),
                first_lecture_date=first_lecture_date,
                requested_count=requested_count,
            )
        span.set_outputs({"lecture_count": len(proposal.lectures)})
        return proposal
