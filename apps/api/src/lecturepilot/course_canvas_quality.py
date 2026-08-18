from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Protocol

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_quality_models import (
    CanvasQualityIssue,
    CanvasQualityPayload,
)
from lecturepilot.course_canvas_quality_prompt import (
    compact_quality_evidence,
    quality_review_batches,
)
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_provider_errors import model_provider_error_message
from lecturepilot.model_request_options import (
    CANVAS_QUALITY_REQUEST_TIMEOUT_SECONDS,
    completion_options,
)
from lecturepilot.model_usage import ModelUsageRecorder, complete_with_usage
from lecturepilot.models import ProviderSettings
from lecturepilot.providers import ProviderConfigurationError


QUALITY_RESPONSE_ATTEMPTS = 2


class CanvasQualityModelClient(Protocol):
    async def complete_review(
        self,
        *,
        settings: ProviderSettings,
        source_document: CanvasDocument,
        candidate_document: CanvasDocument,
    ) -> dict[str, Any]: ...


class LiteLLMCanvasQualityClient:
    def __init__(self, usage_recorder: ModelUsageRecorder | None = None) -> None:
        self.usage_recorder = usage_recorder

    async def complete_review(
        self,
        *,
        settings: ProviderSettings,
        source_document: CanvasDocument,
        candidate_document: CanvasDocument,
    ) -> dict[str, Any]:
        try:
            from litellm import acompletion
        except ImportError as exc:
            raise ProviderConfigurationError(
                'litellm is not installed. Install the backend with the "agent" extra.'
            ) from exc
        messages = _quality_messages(source_document, candidate_document)
        last_error: ModelExecutionError | None = None
        for attempt in range(QUALITY_RESPONSE_ATTEMPTS):
            try:
                response = await complete_with_usage(
                    self.usage_recorder,
                    acompletion,
                    usage_stage="canvas_quality_review",
                    model=settings.model,
                    messages=messages,
                    response_format=canvas_quality_response_format(candidate_document),
                    **completion_options(
                        settings,
                        temperature=0.0,
                        reasoning_effort="low",
                        timeout_seconds=CANVAS_QUALITY_REQUEST_TIMEOUT_SECONDS,
                    ),
                )
            except ProviderConfigurationError:
                raise
            except Exception as exc:
                raise ModelExecutionError(
                    model_provider_error_message(exc, provider=settings.provider)
                ) from exc
            try:
                return _read_quality_response(response, source_document, candidate_document)
            except ModelExecutionError as exc:
                last_error = exc
                if attempt == QUALITY_RESPONSE_ATTEMPTS - 1:
                    raise
                messages = [*messages, _quality_retry_message(str(exc))]
        raise last_error or ModelExecutionError("Canvas quality review returned no response.")


class CanvasQualityReviewer:
    def __init__(self, model_client: CanvasQualityModelClient | None = None) -> None:
        self.model_client = model_client or LiteLLMCanvasQualityClient()

    async def review(
        self,
        *,
        settings: ProviderSettings,
        source_document: CanvasDocument,
        candidate_document: CanvasDocument,
    ) -> list[CanvasQualityIssue]:
        documents = [
            candidate_document.model_copy(update={"sections": sections})
            for sections in quality_review_batches(source_document, candidate_document)
        ]
        payloads = await asyncio.gather(
            *[
                self.model_client.complete_review(
                    settings=settings, source_document=source_document, candidate_document=document
                )
                for document in documents
            ]
        )
        issues = [
            issue
            for payload in payloads
            for issue in CanvasQualityPayload.model_validate(payload).issues
        ]
        return _normalize_coordinates(issues, source_document, candidate_document)

    async def validate(
        self,
        *,
        settings: ProviderSettings,
        source_document: CanvasDocument,
        candidate_document: CanvasDocument,
    ) -> None:
        issues = await self.review(
            settings=settings,
            source_document=source_document,
            candidate_document=candidate_document,
        )
        if not issues:
            return
        first = issues[0]
        details = "; ".join(issue.reason for issue in issues[:5])
        same_section = len({issue.section_id for issue in issues}) == 1
        raise CanvasGenerationRepairableError(
            f"Canvas quality review failed: {details}",
            candidate=candidate_document,
            section_id=first.section_id,
            block_id=None if len(issues) > 1 and same_section else first.block_id,
        )


def canvas_quality_response_format(candidate_document: CanvasDocument) -> dict[str, Any]:
    section_ids = [section.id for section in candidate_document.sections]
    block_ids = [block.id for section in candidate_document.sections for block in section.blocks]
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "lecturepilot_canvas_quality_review",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "issues": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "section_id": {"type": "string", "enum": section_ids},
                                "block_id": {
                                    "type": ["string", "null"],
                                    "enum": [None, *block_ids],
                                },
                                "reason": {"type": "string"},
                            },
                            "required": ["section_id", "block_id", "reason"],
                        },
                    }
                },
                "required": ["issues"],
            },
        },
    }


def _quality_messages(
    source_document: CanvasDocument,
    candidate_document: CanvasDocument,
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "Audit a generated university learning canvas against only the supplied professor "
                "source evidence. Return every material factual, mathematical, code, or answer-key "
                "error. A quiz is invalid when its selected answer is not supported by the source, "
                "when another option is also correct, or when its question and selected answer do "
                "not match. Plausible wrong distractors are allowed only inside quiz options and "
                "must not be reported merely for being false. A checkpoint is an open-answer task "
                "and does not need answer options, an answer key, or a selected answer when its "
                "prompt asks a direct, determinate question or task. "
                "A checkpoint that asks which statement, task, option, or example is correct is "
                "not determinate unless those alternatives are restated in its text. "
                "Report unsupported teaching claims, altered code behavior, wrong formulas, and "
                "contradictions. Also report an "
                "assessment whose task is generic or depends on an exercise sheet, slide, source, "
                "section, or prior question that is not restated. Do not otherwise report style, "
                "wording, missing enrichment, or harmless simplification. Use exact candidate "
                "section ids. For block_id, copy its id verbatim from GENERATED CANDIDATE JSON; "
                "never construct an id from a section or source pattern. If the issue applies to "
                "the section as a whole or no exact candidate block id applies, use null. Return "
                "an empty issues array only when no material issue "
                "remains."
            ),
        },
        {
            "role": "user",
            "content": compact_quality_evidence(source_document, candidate_document),
        },
    ]


def _read_quality_response(
    response: Any,
    source_document: CanvasDocument,
    candidate_document: CanvasDocument,
) -> dict[str, Any]:
    choice = response.choices[0]
    content = choice.message.content
    if not content:
        finish_reason = str(getattr(choice, "finish_reason", "") or "unknown")
        raise ModelExecutionError(
            f"Canvas quality review returned an empty response (finish_reason={finish_reason})."
        )
    try:
        payload = CanvasQualityPayload.model_validate(json.loads(content))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ModelExecutionError(
            "Canvas quality review returned invalid structured JSON."
        ) from exc
    issues = _normalize_coordinates(payload.issues, source_document, candidate_document)
    return {"issues": [issue.model_dump() for issue in issues]}


def _quality_retry_message(error: str) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            f"The previous review response could not be used: {error} "
            "Return one complete, non-truncated JSON response matching the required schema."
        ),
    }


def _normalize_coordinates(
    issues: list[CanvasQualityIssue],
    source_document: CanvasDocument,
    candidate_document: CanvasDocument,
) -> list[CanvasQualityIssue]:
    blocks_by_section = {
        section.id: {block.id for block in section.blocks}
        for section in candidate_document.sections
    }
    section_aliases = _mirrored_section_aliases(source_document, candidate_document)
    normalized: list[CanvasQualityIssue] = []
    for issue in issues:
        section_id = issue.section_id
        if section_id not in blocks_by_section:
            section_id = section_aliases.get(section_id, section_id)
        if section_id not in blocks_by_section:
            raise ModelExecutionError(
                f"Canvas quality review returned unknown section {issue.section_id}."
            )
        updates: dict[str, str | None] = {}
        if section_id != issue.section_id:
            updates["section_id"] = section_id
        if issue.block_id is not None and issue.block_id not in blocks_by_section[section_id]:
            updates["block_id"] = None
        if updates:
            issue = issue.model_copy(update=updates)
        normalized.append(issue)
    return normalized


def _mirrored_section_aliases(
    source_document: CanvasDocument,
    candidate_document: CanvasDocument,
) -> dict[str, str]:
    candidate_ids = {section.id for section in candidate_document.sections}
    aliases: dict[str, str] = {}
    for source_section in source_document.sections:
        pattern = re.compile(rf"^learning-\d+-{re.escape(source_section.id)}(?:-\d+)?$")
        matches = [section_id for section_id in candidate_ids if pattern.fullmatch(section_id)]
        if len(matches) == 1:
            aliases[source_section.id] = matches[0]
    return aliases
