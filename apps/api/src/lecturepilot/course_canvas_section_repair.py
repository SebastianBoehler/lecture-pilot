from __future__ import annotations

import re
from typing import Protocol

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_language import canvas_language_instruction
from lecturepilot.course_canvas_math import generated_math_instructions
from lecturepilot.course_canvas_section_planner import _read_section_payload
from lecturepilot.course_canvas_validation import validate_planned_document
from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.providers import ProviderConfigurationError


class _RepairModel(Protocol):
    async def complete_plan(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
    ) -> dict: ...


class _RepairPlanner(Protocol):
    provider_registry: object
    model_client: _RepairModel


class CourseCanvasSectionRepairMixin:
    async def repair_section(
        self: _RepairPlanner,
        source_document: CanvasDocument,
        candidate_document: CanvasDocument,
        *,
        section_id: str,
        block_id: str | None,
        failure_context: str,
        output_language: str = "en",
    ) -> CanvasDocument:
        section = _section(candidate_document, section_id)
        target = _block(section, block_id) if block_id else None
        settings = self.provider_registry.require_ready(
            [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        )
        messages = _repair_messages(
            source_document,
            section,
            target,
            failure_context,
            output_language=output_language,
        )
        last_error: CanvasGenerationRepairableError | None = None
        for _attempt in range(2):
            repaired: CanvasDocument | None = None
            try:
                payload = await self.model_client.complete_plan(
                    settings=settings,
                    messages=messages,
                )
                replacement = _read_section_payload(
                    payload,
                    section,
                    _allowed_assets(section),
                )
                repaired = _apply_replacement(
                    candidate_document,
                    section,
                    replacement,
                    target,
                )
                validate_planned_document(repaired, source_document)
                return repaired
            except CanvasGenerationRepairableError as exc:
                if repaired is not None and _is_new_target(exc, section, target):
                    raise exc.with_candidate(repaired)
                last_error = exc
                messages = [*messages, _retry_message(str(exc), target)]
            except ProviderConfigurationError:
                raise
        detail = str(last_error or "The proposed section patch is invalid.")
        raise CanvasGenerationRepairableError(
            detail,
            candidate=candidate_document,
            section_id=section.id,
            block_id=target.id if target else None,
        )


def _is_new_target(
    error: CanvasGenerationRepairableError,
    section: CanvasSection,
    target: CanvasBlock | None,
) -> bool:
    if error.section_id is None:
        return False
    if error.section_id != section.id:
        return True
    return target is not None and error.block_id is not None and error.block_id != target.id


def _repair_messages(
    source: CanvasDocument,
    section: CanvasSection,
    target: CanvasBlock | None,
    failure: str,
    *,
    output_language: str,
) -> list[dict[str, str]]:
    scope = (
        "Return one section whose blocks array contains only replacement blocks for the failed "
        "block. Do not repeat or rewrite unchanged blocks. You may replace one mixed prose/math "
        "block with a paragraph or callout followed by a clean math block."
        if target
        else "Return one complete replacement section without changing its topic."
    )
    return [
        {
            "role": "system",
            "content": (
                "You are applying a surgical patch to a generated LecturePilot canvas. "
                f"{canvas_language_instruction(output_language)} "
                f"{scope} Return the standard structured canvas JSON with exactly one section. "
                "Preserve the meaning and use only the supplied evidence. "
                f"{generated_math_instructions()}"
            ),
        },
        {
            "role": "user",
            "content": "\n\n".join(
                [
                    f"Validation failure:\n{failure}",
                    f"Failed section:\n{section.model_dump_json()}",
                    f"Failed block:\n{target.model_dump_json() if target else 'whole section'}",
                    f"Relevant professor source evidence:\n{_source_evidence(source, section)}",
                ]
            ),
        },
    ]


def _retry_message(error: str, target: CanvasBlock | None) -> dict[str, str]:
    scope = "only replacement blocks" if target else "one complete replacement section"
    return {
        "role": "user",
        "content": (
            f"The proposed patch failed validation: {error} "
            f"Return corrected structured JSON containing {scope}."
        ),
    }


def _apply_replacement(
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
        repaired_blocks = _stable_replacement_blocks(
            replacement.blocks,
            target,
            {block.id for block in original.blocks if block.id != target.id},
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


def _stable_replacement_blocks(
    replacements: list[CanvasBlock],
    target: CanvasBlock,
    reserved: set[str],
) -> list[CanvasBlock]:
    if not replacements:
        raise CanvasGenerationRepairableError("The proposed patch returned no replacement blocks.")
    if len(replacements) > 3:
        raise CanvasGenerationRepairableError(
            "A block repair may contain at most 3 replacement blocks."
        )
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
            block_id = _unique_id(f"{target.id}-repair-{repair_index}", reserved)
            repair_index += 1
        reserved.add(block_id)
        result.append(block.model_copy(update={"id": block_id}))
    return result


def _section(document: CanvasDocument, section_id: str) -> CanvasSection:
    section = next((item for item in document.sections if item.id == section_id), None)
    if section is None:
        raise CanvasGenerationRepairableError("The failed section no longer exists.")
    return section


def _block(section: CanvasSection, block_id: str | None) -> CanvasBlock:
    block = next((item for item in section.blocks if item.id == block_id), None)
    if block is None:
        raise CanvasGenerationRepairableError("The failed block no longer exists.")
    return block


def _allowed_assets(section: CanvasSection) -> dict[str, str | None]:
    return {
        block.asset_path: block.asset_url
        for block in section.blocks
        if block.type in {"asset", "video"} and block.asset_path
    }


def _source_evidence(source: CanvasDocument, target: CanvasSection) -> str:
    target_terms = _terms(f"{target.title} {target.source_ref or ''}")
    ranked = sorted(
        source.sections,
        key=lambda section: len(
            target_terms & _terms(f"{section.title} {section.source_ref or ''}")
        ),
        reverse=True,
    )
    selected = ranked[:3]
    evidence = "\n\n".join(section.model_dump_json() for section in selected)
    return evidence[:24_000]


def _terms(value: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9]+", value) if len(token) > 3}


def _unique_id(base: str, reserved: set[str]) -> str:
    candidate = base[:120]
    suffix = 2
    while candidate in reserved:
        tail = f"-{suffix}"
        candidate = f"{base[: 120 - len(tail)]}{tail}"
        suffix += 1
    return candidate
