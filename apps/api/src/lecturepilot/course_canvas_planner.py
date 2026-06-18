from __future__ import annotations

import re
from typing import Protocol

from lecturepilot.agent_response_schema import course_canvas_response_format
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_text_normalizer import clean_canvas_items, clean_canvas_text
from lecturepilot.course_content_filter import filter_source_document_for_planning
from lecturepilot.course_canvas_enrichment import enrich_learning_document
from lecturepilot.course_canvas_ids import avoid_mirrored_section_ids
from lecturepilot.course_canvas_json import parse_model_json
from lecturepilot.course_canvas_prompt import planner_messages, repair_message
from lecturepilot.course_canvas_section_planner import plan_sections_individually
from lecturepilot.course_canvas_validation import validate_planned_document
from lecturepilot.course_slide_interleaving import interleave_original_slides
from lecturepilot.course_planner_warnings import planned_payload, with_payload_warnings
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry

class CoursePlanModelClient(Protocol):
    async def complete_plan(self, *, settings: ProviderSettings, messages: list[dict[str, str]]) -> dict:
        """Return one source-grounded course canvas plan."""
class LiteLLMCoursePlanClient:
    async def complete_plan(self, *, settings: ProviderSettings, messages: list[dict[str, str]]) -> dict:
        try:
            from litellm import acompletion
        except ImportError as exc:
            raise ProviderConfigurationError(
                'litellm is not installed. Install the backend with the "agent" extra.'
            ) from exc

        try:
            response = await acompletion(
                model=settings.model,
                messages=messages,
                max_tokens=18000,
                temperature=0.2,
                response_format=course_canvas_response_format(),
            )
        except Exception as exc:
            raise ModelExecutionError("Course planner model request failed.") from exc
        content = response.choices[0].message.content
        finish_reason = str(getattr(response.choices[0], "finish_reason", "") or "")
        return planned_payload(parse_model_json(content), finish_reason=finish_reason)
class CourseCanvasPlanner:
    def __init__(self, provider_registry: ProviderRegistry | None = None, model_client: CoursePlanModelClient | None = None) -> None:
        self.provider_registry = provider_registry or ProviderRegistry.from_env()
        self.model_client = model_client or LiteLLMCoursePlanClient()

    async def plan_canvas(self, source_document: CanvasDocument) -> CanvasDocument:
        settings = self.provider_registry.require_ready([ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON])
        source_document = filter_source_document_for_planning(source_document)
        messages = planner_messages(source_document)
        last_error: ProviderConfigurationError | None = None
        for _ in range(2):
            try:
                payload = await self.model_client.complete_plan(settings=settings, messages=messages)
                document = avoid_mirrored_section_ids(_planned_document(payload, source_document), source_document)
                document = enrich_learning_document(document)
                document = interleave_original_slides(document, source_document)
                document = with_payload_warnings(document, payload)
                validate_planned_document(document, source_document)
                return document
            except ProviderConfigurationError as exc:
                last_error = exc
                messages = [*messages, repair_message(str(exc), source_document)]
        if last_error:
            sectionwise = await plan_sections_individually(
                model_client=self.model_client,
                settings=settings,
                source_document=source_document,
            )
            sectionwise = avoid_mirrored_section_ids(sectionwise, source_document)
            sectionwise = enrich_learning_document(sectionwise)
            sectionwise = interleave_original_slides(sectionwise, source_document)
            validate_planned_document(sectionwise, source_document)
            return sectionwise
        raise last_error or ProviderConfigurationError("Course planner returned no usable draft.")
def _planned_document(payload: dict, source_document: CanvasDocument) -> CanvasDocument:
    raw_sections = payload.get("sections")
    if not isinstance(raw_sections, list):
        raise ProviderConfigurationError("Course planner JSON must include sections.")
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
        raise ProviderConfigurationError("Course planner returned no usable canvas sections.")
    title = str(payload.get("title") or source_document.title).strip()[:200]
    return source_document.model_copy(
        update={
            "title": title or source_document.title,
            "source_kind": "generated",
            "source_ref": f"course planner from {source_document.source_ref}",
            "sections": sections,
        }
    )


def _read_section(raw_section: object, index: int, allowed_assets: dict[str, str | None]) -> CanvasSection | None:
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


def _read_blocks(raw_blocks: object, section_id: str, allowed_assets: dict[str, str | None]) -> list[CanvasBlock]:
    if not isinstance(raw_blocks, list):
        return []
    blocks: list[CanvasBlock] = []
    counters: dict[str, int] = {}
    for raw_block in raw_blocks[:10]:
        if not isinstance(raw_block, dict):
            continue
        block_type = raw_block.get("type")
        if block_type not in {"paragraph", "list", "callout", "math", "asset", "video", "table", "checkpoint", "quiz"}:
            block_type = "paragraph"
        if block_type in {"asset", "video"} and raw_block.get("asset_path") not in allowed_assets:
            continue
        counters[block_type] = counters.get(block_type, 0) + 1
        block_id = _safe_id(str(raw_block.get("id") or f"{section_id}-{block_type}-{counters[block_type]}"))
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
            text=_trim(clean_canvas_text(raw_block.get("text") or raw_block.get("content")), 700) or None,
        )
    if block_type == "quiz":
        return CanvasBlock(
            id=block_id,
            type="quiz",
            text=_trim(clean_canvas_text(raw_block.get("text") or raw_block.get("question")), 1400),
            items=[_trim(item, 180) for item in clean_canvas_items(_block_items(raw_block)[:6])],
            caption=str(raw_block.get("caption") or raw_block.get("title") or "Checkpoint quiz")[:500],
            answer_index=_answer_index(raw_block),
        )
    if block_type in {"checkpoint", "table"}:
        return CanvasBlock(
            id=block_id,
            type=block_type,
            text=_trim(clean_canvas_text(raw_block.get("text") or raw_block.get("content")), 2400),
            caption=str(raw_block.get("caption") or raw_block.get("title") or "")[:500] or None,
        )
    return CanvasBlock(
        id=block_id,
        type=block_type,
        text=_trim(clean_canvas_text(raw_block.get("text") or raw_block.get("content")), 2400),
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
    cleaned = " ".join(value.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."
