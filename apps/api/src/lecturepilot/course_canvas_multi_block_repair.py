from __future__ import annotations

from typing import Protocol

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_repair_apply import (
    allowed_assets,
    apply_replacement,
    block,
    section,
)
from lecturepilot.course_canvas_repair_prompt import (
    repair_blocks_messages,
    repair_blocks_retry_message,
)
from lecturepilot.course_canvas_repair_response import (
    repair_patch_response_format,
    replacement_edits,
)
from lecturepilot.course_canvas_section_planner import _read_section_payload
from lecturepilot.course_canvas_validation import validate_planned_document
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.providers import ProviderConfigurationError


MULTI_BLOCK_REPAIR_ATTEMPTS = 2


class _RepairModel(Protocol):
    async def complete_plan(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
        temperature: float = 0.4,
        response_format: dict | None = None,
    ) -> dict: ...


class MultiBlockRepairPlanner(Protocol):
    provider_registry: object
    model_client: _RepairModel


async def repair_multiple_blocks(
    planner: MultiBlockRepairPlanner,
    source_document: CanvasDocument,
    candidate_document: CanvasDocument,
    *,
    section_id: str,
    block_ids: list[str],
    failure_context: str,
    output_language: str,
) -> CanvasDocument:
    if len(block_ids) < 2 or len(set(block_ids)) != len(block_ids):
        raise CanvasGenerationRepairableError(
            "A multi-block patch requires at least two distinct block ids."
        )
    original = section(candidate_document, section_id)
    targets = [block(original, block_id) for block_id in block_ids]
    settings = planner.provider_registry.require_ready(
        [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
    )
    messages = repair_blocks_messages(
        source_document,
        original,
        targets,
        failure_context,
        output_language=output_language,
    )
    last_error: CanvasGenerationRepairableError | None = None
    for attempt in range(MULTI_BLOCK_REPAIR_ATTEMPTS):
        try:
            payload = await planner.model_client.complete_plan(
                settings=settings,
                messages=messages,
                temperature=0.4,
                response_format=repair_patch_response_format(),
            )
            edits = replacement_edits(
                payload,
                section_id=section_id,
                block_ids=block_ids,
            )
            repaired = candidate_document
            for target in targets:
                active_section = section(repaired, section_id)
                active_target = block(active_section, target.id)
                replacement = _read_section_payload(
                    {"blocks": edits[target.id]},
                    active_section,
                    allowed_assets(active_section),
                    output_language=output_language,
                    require_checkpoint=active_target.type == "checkpoint",
                )
                repaired = apply_replacement(
                    repaired,
                    active_section,
                    replacement,
                    active_target,
                )
            validate_planned_document(repaired, source_document)
            return repaired
        except CanvasGenerationRepairableError as exc:
            last_error = exc
            if attempt == MULTI_BLOCK_REPAIR_ATTEMPTS - 1:
                break
            messages = [*messages, repair_blocks_retry_message(str(exc), len(targets))]
        except ModelExecutionError as exc:
            if exc.__cause__ is not None or attempt == MULTI_BLOCK_REPAIR_ATTEMPTS - 1:
                raise
        except ProviderConfigurationError:
            raise
    raise CanvasGenerationRepairableError(
        str(last_error or "The proposed multi-block patch is invalid."),
        candidate=candidate_document,
        section_id=section_id,
    )
