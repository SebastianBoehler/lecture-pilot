from __future__ import annotations

from lecturepilot.canvas_component_catalog import normalize_component_identity
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError


def apply_replacement(
    document: CanvasDocument,
    original: CanvasSection,
    replacement: CanvasSection,
    target: CanvasBlock | None,
) -> CanvasDocument:
    if target is None:
        repaired_section = replacement.model_copy(
            update={
                "id": original.id,
                "title": original.title,
                "source_ref": original.source_ref,
            }
        )
    else:
        target_index = next(
            index for index, block in enumerate(original.blocks) if block.id == target.id
        )
        repaired_blocks = stable_replacement_blocks(
            replacement.blocks,
            target,
            {
                block.id
                for section in document.sections
                for block in section.blocks
                if section.id != original.id or block.id != target.id
            },
        )
        repaired_section = original.model_copy(
            update={
                "blocks": [
                    *original.blocks[:target_index],
                    *repaired_blocks,
                    *original.blocks[target_index + 1 :],
                ]
            }
        )
    sections = [
        repaired_section if section.id == original.id else section for section in document.sections
    ]
    return document.model_copy(update={"sections": sections})


def stable_replacement_blocks(
    replacements: list[CanvasBlock],
    target: CanvasBlock,
    reserved: set[str],
) -> list[CanvasBlock]:
    if not replacements:
        raise CanvasGenerationRepairableError("The proposed patch returned no replacement blocks.")
    primary = next(
        (index for index, block in enumerate(replacements) if block.type == target.type),
        len(replacements) - 1,
    )
    result: list[CanvasBlock] = []
    repair_index = 1
    for index, block in enumerate(replacements):
        if index == primary:
            block_id = target.id
        else:
            block_id = unique_id(f"{target.id}-repair-{repair_index}", reserved)
            repair_index += 1
        reserved.add(block_id)
        result.append(normalize_component_identity(block, block_id=block_id))
    return result


def section(document: CanvasDocument, section_id: str) -> CanvasSection:
    found = next((item for item in document.sections if item.id == section_id), None)
    if found is None:
        raise CanvasGenerationRepairableError("The failed section no longer exists.")
    return found


def block(section: CanvasSection, block_id: str | None) -> CanvasBlock:
    found = next((item for item in section.blocks if item.id == block_id), None)
    if found is None:
        raise CanvasGenerationRepairableError("The failed block no longer exists.")
    return found


def allowed_assets(section: CanvasSection) -> dict[str, str | None]:
    return {
        block.asset_path: block.asset_url
        for block in section.blocks
        if block.type in {"asset", "video"} and block.asset_path
    }


def unique_id(base: str, reserved: set[str]) -> str:
    candidate = base[:120]
    suffix = 2
    while candidate in reserved:
        tail = f"-{suffix}"
        candidate = f"{base[: 120 - len(tail)]}{tail}"
        suffix += 1
    return candidate
