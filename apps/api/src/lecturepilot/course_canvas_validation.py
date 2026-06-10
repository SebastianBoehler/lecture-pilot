from __future__ import annotations

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.providers import ProviderConfigurationError


MIN_PLANNED_SECTIONS = 5
MAX_PLANNED_SECTIONS = 8
MIN_DETAIL_CHARS = 600


def validate_planned_document(document: CanvasDocument, source_document: CanvasDocument) -> None:
    section_count = len(document.sections)
    if section_count < MIN_PLANNED_SECTIONS:
        raise ProviderConfigurationError(
            f"Course planner returned {section_count} sections; "
            f"at least {MIN_PLANNED_SECTIONS} are required."
        )
    if section_count > MAX_PLANNED_SECTIONS:
        raise ProviderConfigurationError(
            f"Course planner returned {section_count} sections; "
            f"at most {MAX_PLANNED_SECTIONS} are allowed."
        )
    thin_sections = [section.title for section in document.sections if _teaching_units(section) < 4]
    if thin_sections:
        names = ", ".join(thin_sections[:3])
        raise ProviderConfigurationError(f"Canvas sections need at least 4 teaching blocks: {names}.")
    short_sections = [section.title for section in document.sections if _detail_chars(section) < MIN_DETAIL_CHARS]
    if short_sections:
        names = ", ".join(short_sections[:3])
        raise ProviderConfigurationError(f"Canvas sections need more explanatory detail: {names}.")
    if missing_refs := [section.title for section in document.sections if not section.source_ref]:
        names = ", ".join(missing_refs[:3])
        raise ProviderConfigurationError(f"Canvas sections need source references: {names}.")
    if practice_count(document) < 2:
        raise ProviderConfigurationError("Planned canvas needs one checkpoint and one final retrieval quiz.")
    if quiz_count(document) < 1:
        raise ProviderConfigurationError("Planned canvas needs one final retrieval quiz.")
    mirrored = section_ids(document) & section_ids(source_document)
    if len(mirrored) > max(3, section_count // 2):
        raise ProviderConfigurationError("Course planner mirrored too many extracted slide section ids.")


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
    return sum(1 for section in document.sections for block in section.blocks if block.type == "quiz")


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
