from __future__ import annotations

import re

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_text_normalizer import clean_canvas_items, clean_canvas_text
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_math import normalize_generated_math_block
from lecturepilot.course_canvas_source_ref import planned_source_ref


def planned_document(payload: dict, source_document: CanvasDocument) -> CanvasDocument:
    raw_sections = payload.get("sections")
    if not isinstance(raw_sections, list):
        raise CanvasGenerationRepairableError("Course planner JSON must include sections.")
    allowed_assets = {
        block.asset_path: block.asset_url
        for section in source_document.sections
        for block in section.blocks
        if block.type in {"asset", "video"} and block.asset_path
    }
    sections = [
        section
        for index, raw_section in enumerate(raw_sections[:18], start=1)
        if (section := _read_section(raw_section, index, allowed_assets)) is not None
    ]
    if not sections:
        raise CanvasGenerationRepairableError("Course planner returned no usable canvas sections.")
    title = str(payload.get("title") or source_document.title).strip()[:200]
    return source_document.model_copy(
        update={
            "title": title or source_document.title,
            "source_kind": "generated",
            "source_ref": planned_source_ref(source_document.source_ref),
            "sections": sections,
        }
    )


def _read_section(
    raw_section: object, index: int, allowed_assets: dict[str, str | None]
) -> CanvasSection | None:
    if not isinstance(raw_section, dict):
        return None
    title = str(raw_section.get("title") or f"Canvas section {index}").strip()[:200]
    section_id = _safe_id(str(raw_section.get("id") or title))
    blocks = _read_blocks(raw_section.get("blocks"), section_id, allowed_assets)
    if not blocks:
        return None
    return CanvasSection(
        id=section_id,
        title=title,
        source_ref=str(raw_section.get("source_ref") or "planner source evidence")[:500],
        blocks=blocks,
    )


def _read_blocks(
    raw_blocks: object, section_id: str, allowed_assets: dict[str, str | None]
) -> list[CanvasBlock]:
    if not isinstance(raw_blocks, list):
        return []
    blocks: list[CanvasBlock] = []
    counters: dict[str, int] = {}
    for raw_block in raw_blocks[:10]:
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
        }:
            block_type = "paragraph"
        if block_type in {"asset", "video"} and raw_block.get("asset_path") not in allowed_assets:
            continue
        counters[block_type] = counters.get(block_type, 0) + 1
        block_id = _safe_id(
            str(raw_block.get("id") or f"{section_id}-{block_type}-{counters[block_type]}")
        )
        block = _read_block(raw_block, block_id, block_type, allowed_assets)
        if _is_usable_block(block):
            blocks.append(block)
    return blocks[:8]


def _read_block(
    raw_block: dict,
    block_id: str,
    block_type: str,
    allowed_assets: dict[str, str | None],
) -> CanvasBlock:
    raw_text = clean_canvas_text(raw_block.get("text") or raw_block.get("content"))
    if block_type == "list":
        raw_items = _block_items(raw_block)
        return CanvasBlock(
            id=block_id,
            type="list",
            items=[_trim(item, 340) for item in clean_canvas_items(raw_items[:12])],
        )
    if block_type in {"asset", "video"}:
        asset_path = str(raw_block.get("asset_path"))
        return CanvasBlock(
            id=block_id,
            type=block_type,
            asset_path=asset_path,
            asset_url=allowed_assets.get(asset_path),
            caption=str(raw_block.get("caption") or asset_path)[:500],
            text=_trim(clean_canvas_text(raw_block.get("text") or raw_block.get("content")), 700)
            or None,
        )
    if block_type == "quiz":
        return CanvasBlock(
            id=block_id,
            type="quiz",
            text=_trim(clean_canvas_text(raw_block.get("text") or raw_block.get("question")), 1400),
            items=[_trim(item, 180) for item in clean_canvas_items(_block_items(raw_block)[:6])],
            caption=str(raw_block.get("caption") or raw_block.get("title") or "Checkpoint quiz")[
                :500
            ],
            answer_index=_answer_index(raw_block),
        )
    if block_type in {"checkpoint", "table"}:
        return CanvasBlock(
            id=block_id,
            type=block_type,
            text=_trim(raw_text, 2400),
            caption=str(raw_block.get("caption") or raw_block.get("title") or "")[:500] or None,
        )
    if block_type == "math":
        block_type, raw_text = normalize_generated_math_block(raw_text)
    return CanvasBlock(id=block_id, type=block_type, text=_trim(raw_text, 2400))


def _block_items(raw_block: dict) -> list:
    if isinstance(raw_block.get("items"), list):
        return raw_block["items"]
    if isinstance(raw_block.get("content"), list):
        return raw_block["content"]
    return []


def _answer_index(raw_block: dict) -> int:
    items = _block_items(raw_block)[:6]
    value = raw_block.get("answer_index", raw_block.get("correct_index", 0))
    return value if isinstance(value, int) and 0 <= value < len(items) else 0


def _is_usable_block(block: CanvasBlock) -> bool:
    if block.type in {"asset", "video"}:
        return bool(block.asset_path)
    if block.type == "list":
        return bool(block.items)
    return bool(block.text and block.text.strip())


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.lower()).strip("-")
    return (safe or "canvas-section")[:120]


def _trim(value: str, limit: int) -> str:
    cleaned = (
        value.strip() if value.lstrip().startswith(("```", "~~~")) else " ".join(value.split())
    )
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."
