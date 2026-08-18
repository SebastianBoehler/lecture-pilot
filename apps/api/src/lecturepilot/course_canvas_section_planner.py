from __future__ import annotations

from typing import Protocol

from lecturepilot.canvas_component_catalog import (
    component_block_from_payload,
    component_spec_issue,
)
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_text_normalizer import (
    clean_canvas_items,
    clean_canvas_text,
)
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_evidence_batches import group_evidence_sections
from lecturepilot.course_canvas_math import normalize_generated_math_block, validate_section_math
from lecturepilot.course_canvas_section_batch import SectionPlanResult, plan_section_batch
from lecturepilot.course_canvas_section_checkpoints import (
    SectionPlanCheckpointStore,
    current_section_plan_checkpoint_store,
)
from lecturepilot.course_canvas_section_payload import section_payload as _section_payload
from lecturepilot.course_canvas_section_prompt import section_messages as _section_messages
from lecturepilot.course_canvas_section_values import (
    allowed_assets as _allowed_assets,
    answer_index as _answer_index,
    block_items as _block_items,
    safe_section_id as _safe_id,
)
from lecturepilot.course_canvas_validation import (
    source_topic_sections,
    validate_section_assessments,
)
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderSettings
from lecturepilot.observability import Observability
from lecturepilot.providers import ProviderConfigurationError


SECTION_PLAN_ATTEMPTS = 2


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
    output_language: str = "en",
    repair_context: str | None = None,
    observability: Observability | None = None,
    span_attributes: dict[str, str] | None = None,
    checkpoint_store: SectionPlanCheckpointStore | None = None,
) -> CanvasDocument:
    checkpoint_store = checkpoint_store or current_section_plan_checkpoint_store()
    source_sections = group_evidence_sections(
        source_topic_sections(source_document) or source_document.sections,
        document_source_ref=source_document.source_ref,
    )
    trace = observability or Observability()

    async def plan_one(section_index: int, source_section: CanvasSection) -> SectionPlanResult:
        if checkpoint_store is not None:
            cached = checkpoint_store.read(
                source_section,
                model=settings.model,
                output_language=output_language,
            )
            if cached is not None:
                return SectionPlanResult(cached)
        result = await _plan_section(
            model_client=model_client,
            settings=settings,
            source_document=source_document,
            source_section=source_section,
            output_language=output_language,
            repair_context=repair_context,
            observability=trace,
            span_attributes=span_attributes or {},
            section_index=section_index,
        )
        if checkpoint_store is not None and result.error is None:
            checkpoint_store.write(
                source_section,
                result.section,
                model=settings.model,
                output_language=output_language,
            )
        return result

    if not source_sections:
        raise CanvasGenerationRepairableError("Section planner returned no usable sections.")
    return await plan_section_batch(source_document, source_sections, plan_one)


async def _plan_section(
    *,
    model_client: SectionPlanModelClient,
    settings: ProviderSettings,
    source_document: CanvasDocument,
    source_section: CanvasSection,
    output_language: str,
    repair_context: str | None,
    observability: Observability,
    span_attributes: dict[str, str],
    section_index: int,
) -> SectionPlanResult:
    messages = _section_messages(
        source_document,
        source_section,
        output_language=output_language,
    )
    if repair_context:
        messages.append(
            {"role": "user", "content": f"Avoid this previous generation failure: {repair_context}"}
        )
    allowed_assets = _allowed_assets(source_section)
    last_error: ProviderConfigurationError | ModelExecutionError | None = None
    last_candidate: CanvasSection | None = None
    for attempt in range(1, SECTION_PLAN_ATTEMPTS + 1):
        section: CanvasSection | None = None
        try:
            with observability.model_span(
                stage="section_plan",
                attempt=attempt,
                section_id=source_section.id,
                section_index=section_index,
                **span_attributes,
            ) as span:
                payload = await model_client.complete_plan(settings=settings, messages=messages)
                section = _read_section_payload(payload, source_section, allowed_assets)
                validate_section_math(section)
                validate_section_assessments(section)
                span.set_outputs({"section_count": 1})
                return SectionPlanResult(section)
        except ModelExecutionError as exc:
            last_error = exc
            if exc.__cause__ is not None:
                raise
            messages = [
                *messages,
                {
                    "role": "user",
                    "content": (
                        f"The previous response failed: {exc} "
                        "Return a non-empty JSON section matching the required schema."
                    ),
                },
            ]
        except ProviderConfigurationError as exc:
            if section is not None or last_candidate is None:
                last_error = exc
                last_candidate = section
            messages = [*messages, {"role": "user", "content": f"Repair the section: {exc}"}]
    if isinstance(last_error, CanvasGenerationRepairableError):
        return SectionPlanResult(last_candidate or source_section, last_error)
    if last_error is not None:
        raise last_error
    raise CanvasGenerationRepairableError("Section planner returned invalid JSON.")


def _read_section_payload(
    payload: dict,
    source_section: CanvasSection,
    allowed_assets: dict[str, str | None],
) -> CanvasSection:
    payload = _section_payload(payload)
    section_id = _safe_id(
        str(payload.get("id") or payload.get("section_id") or f"learning-{source_section.id}")
    )
    blocks = _read_blocks(payload.get("blocks"), section_id, allowed_assets)
    if not blocks:
        raise CanvasGenerationRepairableError(f"{source_section.id} has no usable blocks.")
    source_ref = str(source_section.source_ref or "source evidence")
    section = CanvasSection(
        id=section_id,
        title=str(payload.get("title") or source_section.title)[:200],
        source_ref=source_ref[:500],
        blocks=blocks,
    )
    return section


def _read_blocks(
    raw_blocks: object,
    section_id: str,
    allowed_assets: dict[str, str | None],
) -> list[CanvasBlock]:
    if not isinstance(raw_blocks, list):
        return []
    blocks = []
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
        if block_type in {"asset", "video"} and raw_block.get("asset_path") not in allowed_assets:
            continue
        counters[block_type] = counters.get(block_type, 0) + 1
        block = _read_block(
            raw_block,
            f"{section_id}-{block_type}-{counters[block_type]}",
            block_type,
            allowed_assets,
        )
        if block.text or block.items or block.asset_path or block.component_ref:
            blocks.append(block)
    return blocks


def _read_block(
    raw_block: dict,
    block_id: str,
    block_type: str,
    allowed_assets: dict[str, str | None],
) -> CanvasBlock:
    raw_text = clean_canvas_text(raw_block.get("text") or raw_block.get("content"))
    if block_type == "component":
        block = component_block_from_payload(raw_block, block_id)
        if issue := component_spec_issue(block):
            raise CanvasGenerationRepairableError(f"Component block {block_id} {issue}")
        return block
    if block_type == "list":
        raw_items = _block_items(raw_block)
        return CanvasBlock(
            id=block_id,
            type="list",
            items=clean_canvas_items(raw_items),
        )
    if block_type in {"asset", "video"}:
        asset_path = str(raw_block.get("asset_path"))
        return CanvasBlock(
            id=block_id,
            type=block_type,
            asset_path=asset_path,
            asset_url=allowed_assets.get(asset_path),
            caption=str(raw_block.get("caption") or asset_path)[:500],
            text=clean_canvas_text(raw_block.get("text") or raw_block.get("content")) or None,
        )
    if block_type == "quiz":
        return CanvasBlock(
            id=block_id,
            type="quiz",
            text=clean_canvas_text(raw_block.get("text") or raw_block.get("question")),
            items=clean_canvas_items(_block_items(raw_block)[:26]),
            caption=str(raw_block.get("caption") or raw_block.get("title") or "Checkpoint quiz")[
                :500
            ],
            answer_index=_answer_index(raw_block),
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
    return CanvasBlock(
        id=block_id,
        type=block_type,
        text=raw_text,
    )
