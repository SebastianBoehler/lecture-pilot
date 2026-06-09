from __future__ import annotations

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.providers import ProviderConfigurationError


MIN_PLANNED_SECTIONS = 8
MAX_PLANNED_SECTIONS = 14


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
    thin_sections = [section.title for section in document.sections if _content_units(section) < 2]
    if thin_sections:
        names = ", ".join(thin_sections[:3])
        raise ProviderConfigurationError(f"Canvas sections need at least 2 blocks: {names}.")
    missing = [section_id for section_id in required_section_ids(source_document) if section_id not in section_ids(document)]
    if missing:
        names = ", ".join(missing[:5])
        raise ProviderConfigurationError(f"Course planner omitted required sections: {names}.")


def required_section_ids(source_document: CanvasDocument) -> list[str]:
    if len(source_document.sections) < MIN_PLANNED_SECTIONS:
        return []
    return [section.id for section in source_document.sections[:MAX_PLANNED_SECTIONS]]


def section_ids(document: CanvasDocument) -> set[str]:
    return {section.id for section in document.sections}


def _content_units(section) -> int:
    units = 0
    for block in section.blocks:
        if block.type == "list":
            units += min(len(block.items), 3)
        elif block.text or block.asset_path or block.asset_url:
            units += 1
    return units
