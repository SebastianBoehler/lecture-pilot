from __future__ import annotations

import re
from typing import Protocol

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_enrichment import enrich_learning_document
from lecturepilot.course_canvas_json import parse_model_json
from lecturepilot.course_canvas_section_planner import plan_sections_individually
from lecturepilot.course_canvas_validation import required_section_ids, validate_planned_document
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry


MAX_SOURCE_EVIDENCE_SECTIONS = 80


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
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise ModelExecutionError("Course planner model request failed.") from exc
        return parse_model_json(response.choices[0].message.content)


class CourseCanvasPlanner:
    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        model_client: CoursePlanModelClient | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry.from_env()
        self.model_client = model_client or LiteLLMCoursePlanClient()

    async def plan_canvas(self, source_document: CanvasDocument) -> CanvasDocument:
        settings = self.provider_registry.require_ready(
            [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        )
        messages = _planner_messages(source_document)
        last_error: ProviderConfigurationError | None = None
        for _ in range(2):
            try:
                payload = await self.model_client.complete_plan(settings=settings, messages=messages)
                document = enrich_learning_document(_planned_document(payload, source_document))
                validate_planned_document(document, source_document)
                return document
            except ProviderConfigurationError as exc:
                last_error = exc
                messages = [*messages, _repair_message(str(exc), source_document)]
        if last_error:
            sectionwise = await plan_sections_individually(
                model_client=self.model_client,
                settings=settings,
                source_document=source_document,
            )
            sectionwise = enrich_learning_document(sectionwise)
            validate_planned_document(sectionwise, source_document)
            return sectionwise
        raise last_error or ProviderConfigurationError("Course planner returned no usable draft.")


def _planner_messages(source_document: CanvasDocument) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are the LecturePilot course-builder agent. Create an editable, "
                "source-grounded study document from extracted lecture material. "
                "Do not mirror slide-by-slide order, do not preserve extracted slide ids, "
                "and do not create one section per frame. Synthesize the full evidence into "
                "5 to 8 pedagogical sections with stable topic ids, four to seven detailed "
                "teaching blocks per section, key formulas, grouped lists, worked examples, "
                "callouts, infographic briefs, and existing source assets when "
                "they help learning. Collapse long "
                "formula runs into a named derivation with only the essential equations. "
                "Make paragraphs self-study friendly: explain the reason, mechanism, and "
                "consequence in 2 to 4 sentences, then add examples or steps where useful. "
                "Use light Markdown inside text blocks for emphasis, for example "
                "**posterior** or `p(x | C)`, but keep block structure explicit. "
                "Leave room for professor-approved YouTube videos instead of inventing "
                "video links. Return only JSON with title and sections. Each section must "
                "include id, title, source_ref, and blocks. Blocks may be paragraph, list, "
                "callout, math, asset, table, checkpoint, or quiz. Use only 2 "
                "checkpoint or quiz blocks for the full lecture, not after every section. "
                "Quiz blocks use text as the question, items as answers, and answer_index "
                "for the correct option. Asset blocks may only use asset_path values "
                "listed in the evidence. Do not invent unsupported topics. Cite source "
                "files and frames in every source_ref. Never return a short overview."
            ),
        },
        {
            "role": "user",
            "content": _source_evidence(source_document),
        },
    ]


def _repair_message(error: str, source_document: CanvasDocument) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            f"The previous draft failed validation: {error}. Return a corrected JSON draft. "
            "Do not mirror extracted slide ids. Group source evidence into 5 to 8 study "
            "sections, cite source files and frames in source_ref, and use at least 4 "
            "teaching blocks and 600 explanatory characters per section. Source outline ids available for coverage: "
            f"{', '.join(required_section_ids(source_document)) or 'see evidence titles'}."
        ),
    }


def _source_evidence(document: CanvasDocument) -> str:
    lines = [
        f"Course id: {document.course_id}",
        f"Lecture id: {document.lecture_id}",
        f"Lecture title: {document.title}",
        f"Primary source: {document.source_ref}",
        "Extracted source outline; cover these topics but create new learning-section ids:",
    ]
    for index, section in enumerate(document.sections[:MAX_SOURCE_EVIDENCE_SECTIONS], start=1):
        lines.append(f"{index}. id={section.id}; title={section.title}; source_ref={section.source_ref}")
    lines.append("\nExtracted source evidence by outline section:")
    for section in document.sections[:MAX_SOURCE_EVIDENCE_SECTIONS]:
        lines.append(f"\nSECTION {section.id}: {section.title} ({section.source_ref or 'source unknown'})")
        for block in section.blocks:
            lines.append(_block_evidence(block))
    return _trim("\n".join(lines), 50000)


def _block_evidence(block: CanvasBlock) -> str:
    if block.type == "asset":
        return f"- asset id={block.id}; asset_path={block.asset_path}; caption={block.caption or ''}"
    if block.type == "math":
        return f"- math id={block.id}: {_trim(block.text or '', 900)}"
    if block.type == "list":
        items = "; ".join(_trim(item, 180) for item in block.items[:18])
        return f"- list id={block.id}: {items}"
    return f"- {block.type} id={block.id}: {_trim(block.text or '', 900)}"


def _planned_document(payload: dict, source_document: CanvasDocument) -> CanvasDocument:
    raw_sections = payload.get("sections")
    if not isinstance(raw_sections, list):
        raise ProviderConfigurationError("Course planner JSON must include sections.")
    allowed_assets = {
        block.asset_path: block.asset_url
        for section in source_document.sections
        for block in section.blocks
        if block.type == "asset" and block.asset_path
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
        if block_type not in {"paragraph", "list", "callout", "math", "asset", "table", "checkpoint", "quiz"}:
            block_type = "paragraph"
        if block_type == "asset" and raw_block.get("asset_path") not in allowed_assets:
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
            items=[_trim(str(item), 340) for item in raw_items[:12] if str(item).strip()],
        )
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
            text=_trim(str(raw_block.get("text") or raw_block.get("question") or ""), 1400),
            items=[_trim(str(item), 180) for item in _block_items(raw_block)[:6]],
            caption=str(raw_block.get("caption") or raw_block.get("title") or "Checkpoint quiz")[:500],
            answer_index=_answer_index(raw_block),
        )
    if block_type in {"checkpoint", "table"}:
        return CanvasBlock(
            id=block_id,
            type=block_type,
            text=_trim(str(raw_block.get("text") or raw_block.get("content") or ""), 2400),
            caption=str(raw_block.get("caption") or raw_block.get("title") or "")[:500] or None,
        )
    return CanvasBlock(
        id=block_id,
        type=block_type,
        text=_trim(str(raw_block.get("text") or raw_block.get("content") or ""), 2400),
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
    if block.type == "asset":
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
