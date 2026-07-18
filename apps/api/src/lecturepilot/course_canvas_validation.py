from __future__ import annotations

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_math import validate_document_math


MIN_PLANNED_SECTIONS = 5
MIN_FULL_LECTURE_SECTIONS = 8
MAX_SHORT_LECTURE_SECTIONS = 7
MAX_PLANNED_SECTIONS = 12
MIN_DETAIL_CHARS = 600
MIN_PRACTICE_SECTIONS = 3
MIN_QUIZ_BLOCKS = 2


def validate_planned_document(document: CanvasDocument, source_document: CanvasDocument) -> None:
    section_count = len(document.sections)
    min_sections, max_sections = planned_section_bounds(source_document)
    if section_count < min_sections:
        raise CanvasGenerationRepairableError(
            f"Course planner returned {section_count} sections; "
            f"at least {min_sections} are required for this lecture."
        )
    if section_count > max_sections:
        raise CanvasGenerationRepairableError(
            f"Course planner returned {section_count} sections; "
            f"at most {max_sections} are allowed for this lecture."
        )
    validate_document_math(document)
    thin_sections = [section.title for section in document.sections if _teaching_units(section) < 4]
    if thin_sections:
        names = ", ".join(thin_sections[:3])
        raise CanvasGenerationRepairableError(
            f"Canvas sections need at least 4 teaching blocks: {names}."
        )
    short_sections = [
        section.title for section in document.sections if _detail_chars(section) < MIN_DETAIL_CHARS
    ]
    if short_sections:
        names = ", ".join(short_sections[:3])
        raise CanvasGenerationRepairableError(
            f"Canvas sections need more explanatory detail: {names}."
        )
    if missing_refs := [section.title for section in document.sections if not section.source_ref]:
        names = ", ".join(missing_refs[:3])
        raise CanvasGenerationRepairableError(f"Canvas sections need source references: {names}.")
    required_practice, required_quizzes = planned_assessment_requirements(section_count)
    if practice_count(document) < required_practice:
        raise CanvasGenerationRepairableError(
            f"Planned canvas needs assessment blocks in at least {required_practice} sections."
        )
    if quiz_count(document) < required_quizzes:
        raise CanvasGenerationRepairableError(
            f"Planned canvas needs at least {required_quizzes} retrieval quizzes."
        )
    if not any(block.type == "quiz" for block in document.sections[-1].blocks):
        raise CanvasGenerationRepairableError(
            "Planned canvas needs a final-section retrieval quiz."
        )
    mirrored = section_ids(document) & section_ids(source_document)
    if len(mirrored) > max(3, section_count // 2):
        raise CanvasGenerationRepairableError(
            "Course planner mirrored too many extracted slide section ids."
        )


def planned_section_bounds(source_document: CanvasDocument) -> tuple[int, int]:
    topic_count = len(source_topic_sections(source_document))
    if topic_count >= MIN_FULL_LECTURE_SECTIONS:
        return MIN_FULL_LECTURE_SECTIONS, MAX_PLANNED_SECTIONS
    return max(1, min(MIN_PLANNED_SECTIONS, topic_count)), MAX_SHORT_LECTURE_SECTIONS


def source_topic_sections(source_document: CanvasDocument) -> list[CanvasSection]:
    return [section for section in source_document.sections if _is_source_topic(section)]


def planned_assessment_requirements(section_count: int) -> tuple[int, int]:
    practice_sections = min(MIN_PRACTICE_SECTIONS, section_count)
    quiz_blocks = MIN_QUIZ_BLOCKS if section_count >= MIN_PRACTICE_SECTIONS else 1
    return practice_sections, quiz_blocks


def required_section_ids(source_document: CanvasDocument) -> list[str]:
    return []


def section_ids(document: CanvasDocument) -> set[str]:
    return {section.id for section in document.sections}


def practice_count(document: CanvasDocument) -> int:
    return sum(
        1
        for section in document.sections
        if any(block.type in {"checkpoint", "quiz"} for block in section.blocks)
    )


def quiz_count(document: CanvasDocument) -> int:
    return sum(
        1 for section in document.sections for block in section.blocks if block.type == "quiz"
    )


def _teaching_units(section) -> int:
    return sum(
        1
        for block in section.blocks
        if block.type not in {"checkpoint", "quiz"}
        and (block.text or block.items or block.asset_path or block.asset_url)
    )


def _detail_chars(section) -> int:
    return sum(
        len(block.text or "") + sum(len(item) for item in block.items)
        for block in section.blocks
        if block.type not in {"checkpoint", "quiz"}
    )


def _is_source_topic(section) -> bool:
    return any(
        block.type not in {"asset", "video", "checkpoint", "quiz"}
        and (block.text or block.items or block.component_ref)
        for block in section.blocks
    )
