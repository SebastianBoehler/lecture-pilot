from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_prompt import source_evidence
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_request_options import completion_options
from lecturepilot.model_usage import ModelUsageRecorder, complete_with_usage
from lecturepilot.models import ProviderSettings
from lecturepilot.providers import ProviderConfigurationError


class CanvasQualityIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1, max_length=120)
    block_id: str | None = Field(default=None, max_length=120)
    reason: str = Field(min_length=1)


class _CanvasQualityPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issues: list[CanvasQualityIssue] = Field(max_length=30)


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
        try:
            response = await complete_with_usage(
                self.usage_recorder,
                acompletion,
                model=settings.model,
                messages=_quality_messages(source_document, candidate_document),
                response_format=canvas_quality_response_format(),
                **completion_options(
                    settings,
                    temperature=0.0,
                    max_tokens=3000,
                    reasoning_effort="low",
                ),
            )
            return json.loads(response.choices[0].message.content)
        except (ProviderConfigurationError, ModelExecutionError):
            raise
        except Exception as exc:
            raise ModelExecutionError("Canvas quality review model request failed.") from exc


class CanvasQualityReviewer:
    def __init__(self, model_client: CanvasQualityModelClient | None = None) -> None:
        self.model_client = model_client or LiteLLMCanvasQualityClient()

    async def validate(
        self,
        *,
        settings: ProviderSettings,
        source_document: CanvasDocument,
        candidate_document: CanvasDocument,
    ) -> None:
        payload = await self.model_client.complete_review(
            settings=settings,
            source_document=source_document,
            candidate_document=candidate_document,
        )
        issues = _CanvasQualityPayload.model_validate(payload).issues
        _validate_coordinates(issues, candidate_document)
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


def canvas_quality_response_format() -> dict[str, Any]:
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
                                "section_id": {"type": "string"},
                                "block_id": {"type": ["string", "null"]},
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
                "prompt asks a direct, determinate question or task. Report unsupported teaching claims, "
                "altered code behavior, wrong formulas, and contradictions. Also report an "
                "assessment whose task is generic or depends on an exercise sheet, slide, source, "
                "section, or prior question that is not restated. Do not otherwise report style, "
                "wording, missing enrichment, or harmless simplification. Use exact candidate "
                "section and block ids. Return an empty issues array only when no material issue "
                "remains."
            ),
        },
        {
            "role": "user",
            "content": (
                "PROFESSOR SOURCE EVIDENCE\n"
                f"{source_evidence(source_document)}\n\n"
                "GENERATED CANDIDATE JSON\n"
                f"{candidate_document.model_dump_json()}"
            ),
        },
    ]


def _validate_coordinates(
    issues: list[CanvasQualityIssue],
    document: CanvasDocument,
) -> None:
    blocks_by_section = {
        section.id: {block.id for block in section.blocks} for section in document.sections
    }
    for issue in issues:
        if issue.section_id not in blocks_by_section:
            raise ModelExecutionError(
                f"Canvas quality review returned unknown section {issue.section_id}."
            )
        if issue.block_id is not None and issue.block_id not in blocks_by_section[issue.section_id]:
            raise ModelExecutionError(
                f"Canvas quality review returned unknown block {issue.block_id}."
            )
