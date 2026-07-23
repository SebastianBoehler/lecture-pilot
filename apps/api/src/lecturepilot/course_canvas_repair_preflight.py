from __future__ import annotations

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_math import normalize_generated_math_block


def normalize_repair_candidate(
    document: CanvasDocument,
    section_id: str,
    block_id: str | None,
    failure: str,
) -> CanvasDocument:
    lowered = failure.casefold()
    if block_id is None or ("delimiter" not in lowered and "fence" not in lowered):
        return document
    section = next((item for item in document.sections if item.id == section_id), None)
    if section is None:
        raise CanvasGenerationRepairableError("The failed section no longer exists.")
    target = next((item for item in section.blocks if item.id == block_id), None)
    if target is None:
        raise CanvasGenerationRepairableError("The failed block no longer exists.")
    if target.type != "math":
        return document
    block_type, text = normalize_generated_math_block(target.text or "")
    normalized = target.model_copy(update={"type": block_type, "text": text})
    if normalized == target:
        return document
    blocks = [normalized if block.id == block_id else block for block in section.blocks]
    sections = [
        section.model_copy(update={"blocks": blocks}) if item.id == section_id else item
        for item in document.sections
    ]
    return document.model_copy(update={"sections": sections})


def repair_failure_constraint(failure: str) -> str:
    lowered = failure.casefold()
    if "math delimiters" in lowered or "markdown fences" in lowered:
        return (
            r"For this repair, remove every display wrapper such as \[, \], \(, \), $, $$, "
            "```math, or ```latex; the math block itself already provides display context."
        )
    if "unsupported" in lowered or "course-specific" in lowered:
        return "Replace unsupported commands with portable KaTeX commands; do not preserve macros."
    if "explanatory prose" in lowered:
        return (
            "Move explanatory prose into a paragraph or callout and keep only math in math blocks."
        )
    return "Correct only the reported validation failure."
