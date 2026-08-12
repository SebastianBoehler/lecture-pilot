from __future__ import annotations

from lecturepilot.assessment_prompts import assessment_prompt_issue
from lecturepilot.canvas_component_catalog import component_spec_issue
from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_math import validate_document_math


def validate_planned_document(document: CanvasDocument, source_document: CanvasDocument) -> None:
    if not document.sections:
        raise CanvasGenerationRepairableError("Course planner returned no learning sections.")
    validate_document_math(document)
    _validate_quizzes(document)
    _validate_components(document)
    if missing_refs := [section.title for section in document.sections if not section.source_ref]:
        names = ", ".join(missing_refs[:3])
        raise CanvasGenerationRepairableError(f"Canvas sections need source references: {names}.")
    if practice_count(document) < 1:
        raise CanvasGenerationRepairableError(
            "Planned canvas needs at least one source-grounded assessment."
        )


def source_topic_sections(source_document: CanvasDocument) -> list[CanvasSection]:
    return [section for section in source_document.sections if _is_source_topic(section)]


def required_section_ids(source_document: CanvasDocument) -> list[str]:
    return []


def section_ids(document: CanvasDocument) -> set[str]:
    return {section.id for section in document.sections}


def practice_count(document: CanvasDocument) -> int:
    return sum(
        1
        for section in document.sections
        if any(
            block.type in {"checkpoint", "quiz"}
            or (block.type == "component" and block.component_type == "single_choice_quiz")
            for block in section.blocks
        )
    )


def _validate_quizzes(document: CanvasDocument) -> None:
    for section in document.sections:
        validate_section_assessments(section, candidate=document)


def validate_section_assessments(
    section: CanvasSection,
    *,
    candidate: CanvasDocument | None = None,
) -> None:
    for block in section.blocks:
        if block.type not in {"checkpoint", "quiz"}:
            continue
        if issue := assessment_prompt_issue(block.text, block.type):
            raise CanvasGenerationRepairableError(
                f"{block.type.title()} block {block.id} {issue}.",
                candidate=candidate,
                section_id=section.id,
                block_id=block.id,
            )
        if block.type != "quiz":
            continue
        if len(block.items) < 2:
            raise CanvasGenerationRepairableError(
                f"Quiz block {block.id} needs at least 2 answer options.",
                candidate=candidate,
                section_id=section.id,
                block_id=block.id,
            )
        if block.answer_index is None or block.answer_index >= len(block.items):
            raise CanvasGenerationRepairableError(
                f"Quiz block {block.id} needs an explicit valid answer_index.",
                candidate=candidate,
                section_id=section.id,
                block_id=block.id,
            )


def _validate_components(document: CanvasDocument) -> None:
    for section in document.sections:
        for block in section.blocks:
            if block.type != "component":
                continue
            if issue := component_spec_issue(block):
                raise CanvasGenerationRepairableError(
                    f"Component block {block.id} {issue}",
                    candidate=document,
                    section_id=section.id,
                    block_id=block.id,
                )


def _is_source_topic(section) -> bool:
    return any(
        block.type not in {"asset", "video", "checkpoint", "quiz"}
        and (block.text or block.items or block.component_ref)
        for block in section.blocks
    )
