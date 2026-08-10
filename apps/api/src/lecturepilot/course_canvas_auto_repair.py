from __future__ import annotations

from hashlib import sha256
from typing import Protocol

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_validation import validate_planned_document


class CanvasRepairPlanner(Protocol):
    async def repair_section(
        self,
        source_document: CanvasDocument,
        candidate_document: CanvasDocument,
        *,
        section_id: str,
        block_id: str | None,
        failure_context: str,
        output_language: str,
    ) -> CanvasDocument: ...

    async def validate_quality(
        self,
        source_document: CanvasDocument,
        candidate_document: CanvasDocument,
    ) -> None: ...


async def repair_until_quality_valid(
    planner: CanvasRepairPlanner,
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
        digest = sha256(active_candidate.model_dump_json().encode()).hexdigest()
        repair_state = (active_section_id, active_block_id, digest)
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
            repaired = await planner.repair_section(
                source,
                active_candidate,
                section_id=active_section_id,
                block_id=active_block_id,
                failure_context=active_failure,
                output_language=output_language,
            )
            validate_planned_document(repaired, source)
            await planner.validate_quality(source, repaired)
            return repaired
        except CanvasGenerationRepairableError as exc:
            next_candidate = exc.candidate or repaired or active_candidate
            if exc.section_id is None:
                raise exc.with_candidate(next_candidate)
            active_candidate = next_candidate
            active_section_id = exc.section_id
            active_block_id = exc.block_id
            active_failure = str(exc)
