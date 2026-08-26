from __future__ import annotations

from lecturepilot.canvas_component_catalog import component_block_from_payload, component_spec_issue
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.canvas_text_normalizer import clean_canvas_items, clean_canvas_text
from lecturepilot.course_canvas_assessment_normalizer import normalize_section_assessments
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_math import normalize_generated_math_block
from lecturepilot.course_canvas_section_payload import section_payload
from lecturepilot.course_canvas_section_values import answer_index, block_items, safe_section_id


def read_section_payload(
    payload: dict,
    source_section: CanvasSection,
    assets: dict[str, str | None],
    *,
    output_language: str = "en",
    require_checkpoint: bool = True,
) -> CanvasSection:
    payload = section_payload(payload)
    section_id = safe_section_id(
        str(payload.get("id") or payload.get("section_id") or f"learning-{source_section.id}")
    )
    blocks = _read_blocks(payload.get("blocks"), section_id, assets)
    if not blocks:
        raise CanvasGenerationRepairableError(f"{source_section.id} has no usable blocks.")
    section = CanvasSection(
        id=section_id,
        title=str(payload.get("title") or source_section.title)[:200],
        source_ref=str(source_section.source_ref or "source evidence")[:500],
        source_section_id=source_section.source_section_id or source_section.id,
        blocks=blocks,
    )
    return normalize_section_assessments(
        section,
        output_language=output_language,
        require_checkpoint=require_checkpoint,
        fallback_section=source_section,
    )


def _read_blocks(
    raw_blocks: object,
    section_id: str,
    assets: dict[str, str | None],
) -> list[CanvasBlock]:
    if not isinstance(raw_blocks, list):
        return []
    blocks: list[CanvasBlock] = []
    counters: dict[str, int] = {}
    for raw_block in raw_blocks:
        if not isinstance(raw_block, dict):
            continue
        block_type = raw_block.get("type")
        if block_type not in {
            "paragraph",
            "list",
            "callout",
            "math",
            "asset",
            "video",
            "table",
            "checkpoint",
            "quiz",
            "component",
        }:
            block_type = "paragraph"
        if block_type in {"asset", "video"} and raw_block.get("asset_path") not in assets:
            continue
        counters[block_type] = counters.get(block_type, 0) + 1
        generated_id = f"{section_id}-{block_type}-{counters[block_type]}"
        block_id = _canonical_id(raw_block, block_type) or generated_id
        block = _read_block(raw_block, block_id, block_type, assets)
        if block.text or block.items or block.asset_path or block.component_ref:
            blocks.append(block)
    return blocks


def _canonical_id(raw_block: dict, block_type: object) -> str | None:
    block_id = raw_block.get("id")
    if (
        block_type == "checkpoint"
        and isinstance(block_id, str)
        and block_id.startswith("practice-")
    ):
        return block_id
    return None


def _read_block(
    raw_block: dict, block_id: str, block_type: str, assets: dict[str, str | None]
) -> CanvasBlock:
    raw_text = clean_canvas_text(raw_block.get("text") or raw_block.get("content"))
    if block_type == "component":
        block = component_block_from_payload(raw_block, block_id)
        if issue := component_spec_issue(block):
            raise CanvasGenerationRepairableError(f"Component block {block_id} {issue}")
        return block
    if block_type == "list":
        return CanvasBlock(
            id=block_id, type="list", items=clean_canvas_items(block_items(raw_block))
        )
    if block_type in {"asset", "video"}:
        asset_path = str(raw_block.get("asset_path"))
        return CanvasBlock(
            id=block_id,
            type=block_type,
            asset_path=asset_path,
            asset_url=assets.get(asset_path),
            caption=str(raw_block.get("caption") or asset_path)[:500],
            text=clean_canvas_text(raw_block.get("text") or raw_block.get("content")) or None,
        )
    if block_type == "quiz":
        return CanvasBlock(
            id=block_id,
            type="quiz",
            text=clean_canvas_text(raw_block.get("text") or raw_block.get("question")),
            items=clean_canvas_items(block_items(raw_block)[:26]),
            caption=str(raw_block.get("caption") or raw_block.get("title") or "Checkpoint quiz")[
                :500
            ],
            answer_index=answer_index(raw_block),
        )
    if block_type in {"checkpoint", "table"}:
        return CanvasBlock(
            id=block_id,
            type=block_type,
            text=raw_text,
            caption=str(raw_block.get("caption") or raw_block.get("title") or "")[:500] or None,
        )
    if block_type == "math":
        block_type, raw_text = normalize_generated_math_block(raw_text)
    return CanvasBlock(id=block_id, type=block_type, text=raw_text)
