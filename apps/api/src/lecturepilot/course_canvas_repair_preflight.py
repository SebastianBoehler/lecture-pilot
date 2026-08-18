from __future__ import annotations

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_assessment_normalizer import (
    normalize_section_assessments,
    retrieval_checkpoint_text,
)
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_math import math_block_error, normalize_generated_math_block


def normalize_repair_candidate(
    document: CanvasDocument,
    section_id: str,
    block_id: str | None,
    failure: str,
    *,
    output_language: str = "en",
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
    if (
        target.type == "component"
        and target.component_type == "single_choice_quiz"
        and any(marker in lowered for marker in ("at least two options", "explicit correct answer"))
    ):
        checkpoint = target.model_copy(
            update={
                "type": "checkpoint",
                "caption": "Checkpoint",
                "items": [],
                "answer_index": None,
                "component_id": None,
                "component_type": None,
                "component_ref": None,
                "component_version": None,
                "option_ids": [],
                "component_data": None,
            }
        )
        normalized_section = normalize_section_assessments(
            section.model_copy(
                update={
                    "blocks": [checkpoint if item.id == block_id else item for item in section.blocks]
                }
            ),
            output_language=output_language,
            require_checkpoint=False,
            fallback_section=section,
        )
        return document.model_copy(
            update={
                "sections": [
                    normalized_section if item.id == section_id else item
                    for item in document.sections
                ]
            }
        )
    if target.type == "checkpoint" and (
        "unsupported interpretation" in lowered
        or "does not state or explain a relationship" in lowered
        or "does not explain a statement or identify a relationship" in lowered
    ):
        if text := retrieval_checkpoint_text(section, output_language=output_language):
            normalized = target.model_copy(update={"text": text})
            return document.model_copy(
                update={
                    "sections": [
                        section.model_copy(
                            update={
                                "blocks": [
                                    normalized if item.id == block_id else item
                                    for item in section.blocks
                                ]
                            }
                        )
                        if item.id == section_id
                        else item
                        for item in document.sections
                    ]
                }
            )
    if target.type == "checkpoint":
        normalized_section = normalize_section_assessments(
            section,
            output_language=output_language,
            require_checkpoint=False,
            fallback_section=section,
        )
        if normalized_section != section:
            sections = [
                normalized_section if item.id == section_id else item for item in document.sections
            ]
            return document.model_copy(update={"sections": sections})
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
    if "component block" in lowered and any(
        marker in lowered
        for marker in (
            "chart_type",
            "frame",
            "component_data",
            "numeric value",
            "labeled axes",
            "row_labels",
            "matrix",
        )
    ):
        return (
            "Rebuild the failed component_data as one complete payload for its component_type. "
            "For an interactive chart, include a supported chart_type and at least one frame, "
            "plus every labels, values, points, matrix, row_labels, axes, and control field the "
            "selected chart type requires. Use only numeric values present in the evidence."
        )
    if "component block" in lowered and any(
        marker in lowered for marker in ("at least two options", "explicit correct answer")
    ):
        return (
            "Rebuild the single-choice component with at least two options, stable option_ids, "
            "and exactly one explicit correct answer whose answer_index matches the evidence."
        )
    if "math delimiters" in lowered or "markdown fences" in lowered:
        return (
            r"For this repair, remove every display wrapper such as \[, \], \(, \), $, $$, "
            "```math, or ```latex; the math block itself already provides display context."
        )
    if any(
        marker in lowered
        for marker in (
            "source evidence does not establish",
            "unsupported claim",
            "claim is not supported",
            "claim that is not supported",
            "not supported by the supplied source",
            "not stated in the supplied source",
            "misattributes",
        )
    ):
        return (
            "Remove every unsupported factual claim identified by the reviewer. Only replace a "
            "removed claim when the supplied evidence explicitly supports the replacement; do "
            "not infer missing results or preserve a claim by merely qualifying its wording."
        )
    if ("unsupported" in lowered and "math block" in lowered) or any(
        marker in lowered for marker in ("course-specific command", "course-specific macro")
    ):
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
