from __future__ import annotations
from lecturepilot.course_teaching_instructions import (
    media_review_instruction,
    source_explanation_instruction,
)
from lecturepilot.assessment_alignment import assessment_alignment_instruction

import asyncio
import re
from typing import Any, Protocol

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_quality_models import (
    CanvasQualityIssue,
    CanvasQualityPayload,
)
from lecturepilot.course_canvas_quality_prompt import (
    compact_quality_evidence,
    quality_review_batches,
)
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.native_completion import native_completion
from lecturepilot.model_usage import ModelUsageRecorder
from lecturepilot.models import ProviderSettings


QUALITY_RESPONSE_ATTEMPTS = 2


class CanvasQualityModelClient(Protocol):
    async def complete_review(
        self,
        *,
        settings: ProviderSettings,
        source_document: CanvasDocument,
        candidate_document: CanvasDocument,
    ) -> dict[str, Any]: ...


class NativeCanvasQualityClient:
    def __init__(self, usage_recorder: ModelUsageRecorder | None = None, *, model=None) -> None:
        self.usage_recorder, self.model = usage_recorder, model

    async def complete_review(
        self,
        *,
        settings: ProviderSettings,
        source_document: CanvasDocument,
        candidate_document: CanvasDocument,
    ) -> dict[str, Any]:
        def validate(payload):
            parsed = CanvasQualityPayload.model_validate(payload)
            issues = _normalize_coordinates(parsed.issues, source_document, candidate_document)
            return {"issues": [issue.model_dump() for issue in issues]}

        return await native_completion(
            settings=settings,
            messages=_quality_messages(source_document, candidate_document),
            response_format=canvas_quality_response_format(candidate_document),
            stage="canvas_quality_review",
            tier="critic",
            recorder=self.usage_recorder,
            model=self.model,
            reasoning_effort="medium",
            validate=validate,
        )


class CanvasQualityReviewer:
    def __init__(self, model_client: CanvasQualityModelClient | None = None) -> None:
        self.model_client = model_client or NativeCanvasQualityClient()

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
                f"contradictions. {media_review_instruction()} Also report an "
                "assessment whose task is generic or depends on an exercise sheet, slide, source, "
                "section, or prior question that is not restated. Do not otherwise report style, "
                "wording, missing enrichment, or harmless simplification. Report missing instruction needed to solve "
                "an approved practice-* checkpoint when the necessary method or distinction is "
                "in the supplied source but absent from teaching blocks. The task itself does not "
                "count as explanation. Do not demand extra topics beyond the supplied source. Use exact candidate "
                "section ids. For block_id, copy its id verbatim from GENERATED CANDIDATE JSON; "
                "never construct an id from a section or source pattern. If the issue applies to "
                "the section as a whole or no exact candidate block id applies, use null. Return "
                "an empty issues array only when no material issue "
                "remains." + assessment_alignment_instruction() + source_explanation_instruction()
            ),
        },
        {
            "role": "user",
            "content": compact_quality_evidence(source_document, candidate_document),
        },
    ]


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
