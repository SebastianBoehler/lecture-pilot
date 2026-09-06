from __future__ import annotations

from typing import TYPE_CHECKING

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_practice_contract import validate_practice_candidate
from lecturepilot.course_practice_design_models import PracticeDesign

if TYPE_CHECKING:
    from lecturepilot.course_canvas_auto_repair import CanvasRepairPlanner


async def repair_structural_targets(
    planner: CanvasRepairPlanner,
    *,
    source: CanvasDocument,
    candidate: CanvasDocument,
    section_id: str,
    block_id: str | None,
    failure_context: str,
    output_language: str,
    practice_design: PracticeDesign,
) -> CanvasDocument:
    # Advance only through existing targets, never an unbounded model-generated repair loop.
    remaining = {(section.id, None) for section in candidate.sections}
    remaining.update(
        (section.id, block.id) for section in candidate.sections for block in section.blocks
    )
    while (section_id, block_id) in remaining:
        remaining.remove((section_id, block_id))
        try:
            return await planner.repair_section(
                source,
                candidate,
                section_id=section_id,
                block_id=block_id,
                failure_context=failure_context,
                output_language=output_language,
                practice_design=practice_design,
            )
        except CanvasGenerationRepairableError as exc:
            next_target = (exc.section_id, exc.block_id)
            if exc.candidate is None or exc.candidate == candidate or next_target not in remaining:
                raise exc.with_candidate(exc.candidate or candidate)
            validate_practice_candidate(exc.candidate, practice_design, source_document=source)
            candidate = exc.candidate
            section_id, block_id = next_target
            failure_context = str(exc)
    raise CanvasGenerationRepairableError(
        failure_context, candidate=candidate, section_id=section_id, block_id=block_id
    )
