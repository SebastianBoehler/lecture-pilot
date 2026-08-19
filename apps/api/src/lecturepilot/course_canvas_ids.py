from __future__ import annotations

from lecturepilot.canvas_component_catalog import normalize_component_identity
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument
from lecturepilot.course_canvas_validation import section_ids


def avoid_mirrored_section_ids(
    document: CanvasDocument, source_document: CanvasDocument
) -> CanvasDocument:
    source_ids = section_ids(source_document)
    if not source_ids:
        return document
    seen: set[str] = set()
    sections = []
    changed = False
    for index, section in enumerate(document.sections, start=1):
        section_id = section.id
        if section_id in source_ids:
            section_id = f"learning-{index}-{section_id}"
        section_id = _unique_id(section_id, seen)
        blocks = [
            _rename_block(block, old_prefix=section.id, new_prefix=section_id)
            for block in section.blocks
        ]
        changed = changed or section_id != section.id
        sections.append(
            section.model_copy(update={"id": section_id, "blocks": blocks})
            if section_id != section.id
            else section
        )
    normalized = document.model_copy(update={"sections": sections}) if changed else document
    return ensure_unique_block_ids(normalized)


def ensure_unique_block_ids(document: CanvasDocument) -> CanvasDocument:
    seen: set[str] = set()
    sections = []
    changed = False
    for section in document.sections:
        blocks = []
        for block in section.blocks:
            block_id = _unique_id(block.id, seen)
            changed = changed or block_id != block.id
            blocks.append(
                normalize_component_identity(block, block_id=block_id)
                if block_id != block.id
                else block
            )
        sections.append(section.model_copy(update={"blocks": blocks}))
    return document.model_copy(update={"sections": sections}) if changed else document


def _rename_block(block: CanvasBlock, *, old_prefix: str, new_prefix: str) -> CanvasBlock:
    if not block.id.startswith(old_prefix):
        return block
    return block.model_copy(update={"id": block.id.replace(old_prefix, new_prefix, 1)})


def _unique_id(section_id: str, seen: set[str]) -> str:
    candidate = section_id
    suffix = 2
    while candidate in seen:
        candidate = f"{section_id}-{suffix}"
        suffix += 1
    seen.add(candidate)
    return candidate
