from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_ids import avoid_mirrored_section_ids
from lecturepilot.course_canvas_source_ref import planned_source_ref


SECTION_PLAN_CONCURRENCY = 3


@dataclass(frozen=True)
class SectionPlanResult:
    section: CanvasSection
    error: CanvasGenerationRepairableError | None = None


async def plan_section_batch(
    source_document: CanvasDocument,
    source_sections: list[CanvasSection],
    worker: Callable[[int, CanvasSection], Awaitable[SectionPlanResult]],
) -> CanvasDocument:
    semaphore = asyncio.Semaphore(SECTION_PLAN_CONCURRENCY)

    async def run(index: int, source_section: CanvasSection) -> SectionPlanResult:
        async with semaphore:
            return await worker(index, source_section)

    results = await asyncio.gather(
        *(run(index, section) for index, section in enumerate(source_sections, start=1))
    )
    raw_candidate = source_document.model_copy(
        update={
            "source_kind": "generated",
            "source_ref": planned_source_ref(source_document.source_ref),
            "sections": [result.section for result in results],
        }
    )
    candidate = avoid_mirrored_section_ids(raw_candidate, source_document)
    for index, result in enumerate(results):
        if result.error is not None:
            raise _retarget(result.error, raw_candidate, candidate, index).with_candidate(candidate)
    return candidate


def _retarget(
    error: CanvasGenerationRepairableError,
    before: CanvasDocument,
    after: CanvasDocument,
    section_index: int,
) -> CanvasGenerationRepairableError:
    old_section = before.sections[section_index]
    new_section = after.sections[section_index]
    old_block_index = next(
        (index for index, block in enumerate(old_section.blocks) if block.id == error.block_id),
        None,
    )
    error.section_id = new_section.id
    error.block_id = new_section.blocks[old_block_index].id if old_block_index is not None else None
    return error
