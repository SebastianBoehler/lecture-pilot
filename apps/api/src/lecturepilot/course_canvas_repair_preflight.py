from __future__ import annotations

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_math import math_block_error, normalize_generated_math_block


def normalize_repair_candidate(
    document: CanvasDocument,
    section_id: str,
    block_id: str | None,
    failure: str,
) -> CanvasDocument:
    lowered = failure.casefold()
    if block_id is None:
        return document
    section = next((item for item in document.sections if item.id == section_id), None)
    if section is None:
        raise CanvasGenerationRepairableError("The failed section no longer exists.")
    target = next((item for item in section.blocks if item.id == block_id), None)
    if target is None:
        raise CanvasGenerationRepairableError("The failed block no longer exists.")
    if target.type != "math" or not any(
        marker in lowered
        for marker in (
            "math block",
            "delimiter",
            "fence",
            "unsupported command",
            "explanatory prose",
        )
    ):
        return document
    current_error = (math_block_error(target.text or "") or "").casefold()
    if "unsupported" in lowered and "unsupported" not in current_error:
        return document
    if "explanatory prose" in lowered and "explanatory prose" not in current_error:
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
    if any(
        marker in lowered
        for marker in (
            "understandable without",
            "depends on",
            "not restated",
            "cannot determine",
            "omitted exercise",
        )
    ):
        return (
            "Make the assessment fully standalone by including every value, definition, table "
            "entry, and premise needed to answer it. Never refer to a sheet, slide, source, prior "
            "question, or omitted context. If the supplied evidence is insufficient to create a "
            "determinate standalone assessment, replace the failed assessment with an accurate "
            "teaching paragraph instead of inventing data."
        )
    if any(
        marker in lowered
        for marker in (
            "direct question",
            "concrete task",
            "generic assessment scaffolding",
            "labels in caption",
            "options that are not stated",
        )
    ):
        return (
            "Rewrite the assessment text as one specific, standalone, source-grounded question "
            "ending in ? or as one concrete imperative task. State exactly what answer, "
            "calculation, comparison, derivation, or justification the learner must produce."
        )
    return "Correct only the reported validation failure."
