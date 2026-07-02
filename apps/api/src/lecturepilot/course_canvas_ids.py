from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument
from lecturepilot.course_canvas_validation import section_ids


def avoid_mirrored_section_ids(document: CanvasDocument, source_document: CanvasDocument) -> CanvasDocument:
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
        if section_id == section.id:
            sections.append(section)
            continue
        changed = True
        sections.append(
            section.model_copy(
                update={
                    "id": section_id,
                    "blocks": [_rename_block(block, old_prefix=section.id, new_prefix=section_id) for block in section.blocks],
                }
            )
        )
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
