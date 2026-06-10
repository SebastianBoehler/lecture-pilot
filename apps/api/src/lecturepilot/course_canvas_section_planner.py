from __future__ import annotations

from typing import Protocol

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_validation import MAX_PLANNED_SECTIONS
from lecturepilot.models import ProviderSettings
from lecturepilot.providers import ProviderConfigurationError


class SectionPlanModelClient(Protocol):
    async def complete_plan(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
    ) -> dict:
        """Return one section-level canvas plan."""


async def plan_sections_individually(
    *,
    model_client: SectionPlanModelClient,
    settings: ProviderSettings,
    source_document: CanvasDocument,
) -> CanvasDocument:
    sections = []
    for source_section in source_document.sections[:MAX_PLANNED_SECTIONS]:
        sections.append(
            await _plan_section(
                model_client=model_client,
                settings=settings,
                source_document=source_document,
                source_section=source_section,
            )
        )
    if not sections:
        raise ProviderConfigurationError("Section planner returned no usable sections.")
    return source_document.model_copy(
        update={
            "source_kind": "generated",
            "source_ref": f"course planner from {source_document.source_ref}",
            "sections": sections,
        }
    )


async def _plan_section(
    *,
    model_client: SectionPlanModelClient,
    settings: ProviderSettings,
    source_document: CanvasDocument,
    source_section: CanvasSection,
) -> CanvasSection:
    messages = _section_messages(source_document, source_section)
    allowed_assets = _allowed_assets(source_section)
    last_error: ProviderConfigurationError | None = None
    for _ in range(2):
        try:
            payload = await model_client.complete_plan(settings=settings, messages=messages)
            return _read_section_payload(payload, source_section, allowed_assets)
        except ProviderConfigurationError as exc:
            last_error = exc
            messages = [*messages, {"role": "user", "content": f"Repair the section: {exc}"}]
    raise last_error or ProviderConfigurationError("Section planner returned invalid JSON.")


def _section_messages(source_document: CanvasDocument, section: CanvasSection) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Rewrite this extracted lecture section into a clean markdown learning "
                "canvas section. Return JSON only with id, title, source_ref, and blocks. "
                "Use 2 to 5 blocks. Blocks may be paragraph, list, callout, math, asset, "
                "table, checkpoint, or quiz. Quiz blocks use text as the question and "
                "items as possible answers plus answer_index for the correct option. "
                "Do not preserve raw slide ids; create a stable learning topic id. Preserve "
                "key formulas and source-backed assets. Add a worked example or infographic "
                "brief when it helps learning. Use light Markdown for key terms and notation. "
                "Do not invent unsupported topics."
            ),
        },
        {
            "role": "user",
            "content": _section_evidence(source_document, section),
        },
    ]


def _section_evidence(source_document: CanvasDocument, section: CanvasSection) -> str:
    lines = [
        f"Course id: {source_document.course_id}",
        f"Lecture id: {source_document.lecture_id}",
        f"Primary source: {source_document.source_ref}",
        f"Required section id: {section.id}",
        f"Source section title: {section.title}",
        f"Source frames: {section.source_ref or 'unknown'}",
    ]
    for block in section.blocks:
        if block.type == "asset":
            lines.append(f"- asset asset_path={block.asset_path}; caption={block.caption or ''}")
        elif block.type == "list":
            lines.append("- list: " + "; ".join(block.items[:24]))
        else:
            lines.append(f"- {block.type}: {block.text or ''}")
    return _trim("\n".join(lines), 12000)


def _read_section_payload(
    payload: dict,
    source_section: CanvasSection,
    allowed_assets: dict[str, str | None],
) -> CanvasSection:
    payload = _section_payload(payload)
    section_id = _safe_id(str(payload.get("id") or payload.get("section_id") or f"learning-{source_section.id}"))
    blocks = _read_blocks(payload.get("blocks"), section_id, allowed_assets)
    if not blocks:
        raise ProviderConfigurationError(f"{source_section.id} has no usable blocks.")
    source_ref = str(payload.get("source_ref") or source_section.source_ref or "source evidence")
    return CanvasSection(
        id=section_id,
        title=str(payload.get("title") or source_section.title)[:200],
        source_ref=source_ref[:500],
        blocks=blocks,
    )


def _section_payload(payload: dict) -> dict:
    if isinstance(payload.get("section"), dict):
        payload = payload["section"]
    elif isinstance(payload.get("sections"), list) and payload["sections"]:
        first = payload["sections"][0]
        if isinstance(first, dict):
            payload = first
    if isinstance(payload.get("blocks"), list):
        return payload
    blocks = _blocks_from_common_keys(payload)
    return {**payload, "blocks": blocks}


def _blocks_from_common_keys(payload: dict) -> list[dict]:
    blocks: list[dict] = []
    for key in ("summary", "content", "text", "paragraph"):
        if isinstance(payload.get(key), str) and payload[key].strip():
            blocks.append({"type": "paragraph", "text": payload[key]})
            break
    for key in ("key_points", "items", "bullets"):
        if isinstance(payload.get(key), list):
            blocks.append({"type": "list", "items": payload[key]})
            break
    for key in ("formula", "formulas", "math"):
        value = payload.get(key)
        if isinstance(value, str):
            blocks.append({"type": "math", "text": value})
        elif isinstance(value, list):
            blocks.extend({"type": "math", "text": item} for item in value if isinstance(item, str))
        if value:
            break
    for key in ("callout", "example", "infographic_brief"):
        if isinstance(payload.get(key), str) and payload[key].strip():
            blocks.append({"type": "callout", "text": payload[key]})
            break
    return blocks


def _read_blocks(
    raw_blocks: object,
    section_id: str,
    allowed_assets: dict[str, str | None],
) -> list[CanvasBlock]:
    if not isinstance(raw_blocks, list):
        return []
    blocks = []
    counters: dict[str, int] = {}
    for raw_block in raw_blocks[:6]:
        if not isinstance(raw_block, dict):
            continue
        block_type = raw_block.get("type")
        if block_type not in {"paragraph", "list", "callout", "math", "asset", "table", "checkpoint", "quiz"}:
            block_type = "paragraph"
        if block_type == "asset" and raw_block.get("asset_path") not in allowed_assets:
            continue
        counters[block_type] = counters.get(block_type, 0) + 1
        block = _read_block(
            raw_block,
            f"{section_id}-{block_type}-{counters[block_type]}",
            block_type,
            allowed_assets,
        )
        if block.text or block.items or block.asset_path:
            blocks.append(block)
    return blocks


def _read_block(
    raw_block: dict,
    block_id: str,
    block_type: str,
    allowed_assets: dict[str, str | None],
) -> CanvasBlock:
    if block_type == "list":
        raw_items = _block_items(raw_block)
        return CanvasBlock(id=block_id, type="list", items=[_trim(str(item), 260) for item in raw_items[:10]])
    if block_type == "asset":
        asset_path = str(raw_block.get("asset_path"))
        return CanvasBlock(
            id=block_id,
            type="asset",
            asset_path=asset_path,
            asset_url=allowed_assets.get(asset_path),
            caption=str(raw_block.get("caption") or asset_path)[:500],
        )
    if block_type == "quiz":
        return CanvasBlock(
            id=block_id,
            type="quiz",
            text=_trim(str(raw_block.get("text") or raw_block.get("question") or ""), 1000),
            items=[_trim(str(item), 180) for item in _block_items(raw_block)[:6]],
            caption=str(raw_block.get("caption") or raw_block.get("title") or "Checkpoint quiz")[:500],
            answer_index=_answer_index(raw_block),
        )
    if block_type in {"checkpoint", "table"}:
        return CanvasBlock(
            id=block_id,
            type=block_type,
            text=_trim(str(raw_block.get("text") or raw_block.get("content") or ""), 1600),
            caption=str(raw_block.get("caption") or raw_block.get("title") or "")[:500] or None,
        )
    return CanvasBlock(
        id=block_id,
        type=block_type,
        text=_trim(str(raw_block.get("text") or raw_block.get("content") or ""), 1600),
    )


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


def _allowed_assets(section: CanvasSection) -> dict[str, str | None]:
    return {
        block.asset_path: block.asset_url
        for block in section.blocks
        if block.type == "asset" and block.asset_path
    }


def _safe_id(value: str) -> str:
    safe = "".join(char.lower() if char.isalnum() else "-" for char in value)
    return "-".join(part for part in safe.split("-") if part)[:120] or "learning-section"


def _trim(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."
