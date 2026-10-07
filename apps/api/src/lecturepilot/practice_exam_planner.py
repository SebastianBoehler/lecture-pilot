from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
import logging
import os
from typing import Protocol
from uuid import uuid4

from pydantic import ValidationError

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.model_usage import ModelUsageRecorder
from lecturepilot.native_completion import native_completion
from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.practice_exam_models import (
    PracticeExam,
    PracticeExamQuestion,
    MULTIPLE_SELECT_POINTS,
    sanitize_practice_exam_instructions,
)
from lecturepilot.practice_exam_prompt import (
    authoritative_canvas_evidence,
    ppi_pattern_evidence,
    practice_exam_messages,
    practice_exam_review_messages,
)
from lecturepilot.practice_exam_schema import (
    practice_exam_response_format,
    practice_exam_review_response_format,
)
from lecturepilot.practice_exam_validation import (
    PracticeExamValidationError,
    validate_practice_exam,
    validate_practice_exam_review,
)
from lecturepilot.practice_exam_solution_review import verify_open_answer_sheet
from lecturepilot.practice_exam_repair import repair_request, merge_question_repairs
from lecturepilot.providers import ProviderRegistry


logger = logging.getLogger(__name__)


class PracticeExamPlanningError(ValueError):
    pass


class PracticeExamModelClient(Protocol):
    async def complete_exam(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
        response_format: dict,
        max_tokens: int,
    ) -> dict:
        """Return a structured practice exam authoring payload."""


class NativePracticeExamClient:
    def __init__(self, usage_recorder: ModelUsageRecorder | None = None) -> None:
        self.usage_recorder = usage_recorder

    async def complete_exam(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
        response_format: dict,
        max_tokens: int,
    ) -> dict:
        review = response_format["json_schema"].get("name") == "lecturepilot_practice_exam_review"
        return await native_completion(
            settings=settings,
            messages=messages,
            response_format=response_format,
            stage="practice_exam_review" if review else "practice_exam",
            tier="critic" if review else None,
            recorder=self.usage_recorder,
            temperature=0.2,
            max_tokens=max_tokens,
            reasoning_effort="high",
        )


class PracticeExamPlanner:
    def __init__(
        self,
        *,
        provider_registry: ProviderRegistry | None = None,
        model_client: PracticeExamModelClient | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry.from_env(
            model=os.getenv("LECTUREPILOT_PRACTICE_EXAM_MODEL") or None
        )
        self.model_client = model_client or NativePracticeExamClient()

    async def plan(
        self,
        *,
        course_id: str,
        course_title: str,
        language: str,
        duration_minutes: int,
        question_count: int,
        documents: list[CanvasDocument],
        ppi_sources: dict[str, list[str]],
        choice_format: str = "single_answer",
        learner_focus: list[dict] | None = None,
    ) -> PracticeExam:
        course_evidence, authoritative_ids = authoritative_canvas_evidence(documents)
        if not authoritative_ids:
            raise PracticeExamPlanningError(
                "Practice exam generation requires unlocked course content."
            )
        settings = self.provider_registry.require_ready(
            [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        )
        ppi_evidence = ppi_pattern_evidence(ppi_sources)
        ppi_texts = [text for texts in ppi_sources.values() for text in texts]
        response_format = practice_exam_response_format(
            question_count=question_count,
            authoritative_source_ids=authoritative_ids,
            selected_ppi_source_ids=set(ppi_sources),
            choice_format=choice_format,
        )
        repair_error: str | None = None
        last_error: Exception | None = None
        candidate: dict | None = None
        rejected_ids: list[str] = []
        for attempt in range(2):
            messages = practice_exam_messages(
                course_title=course_title,
                language=language,
                duration_minutes=duration_minutes,
                question_count=question_count,
                course_evidence=course_evidence,
                ppi_evidence=ppi_evidence,
                repair_error=repair_error,
                choice_format=choice_format,
                learner_focus=learner_focus,
            )
            current_format = response_format
            if candidate is not None and rejected_ids:
                messages, current_format = repair_request(
                    messages, response_format, candidate, rejected_ids
                )
            payload = await self.model_client.complete_exam(
                settings=settings,
                response_format=current_format,
                max_tokens=_exam_output_token_budget(len(rejected_ids) or question_count),
                messages=messages,
            )
            try:
                if candidate is not None and rejected_ids:
                    payload = merge_question_repairs(candidate, payload, rejected_ids)
                candidate = payload
                exam = _exam_from_payload(
                    payload,
                    course_id=course_id,
                    language=language,
                    duration_minutes=duration_minutes,
                    source_revision=_source_revision(course_evidence, ppi_sources),
                    ppi_source_ids=sorted(ppi_sources),
                )
                validate_practice_exam(
                    exam,
                    authoritative_source_ids=authoritative_ids,
                    question_count=question_count,
                    selected_ppi_source_ids=set(ppi_sources),
                    ppi_texts=ppi_texts,
                    choice_format=choice_format,
                )
                review = await self.model_client.complete_exam(
                    settings=settings,
                    messages=practice_exam_review_messages(
                        course_evidence=course_evidence,
                        exam=exam,
                    ),
                    response_format=practice_exam_review_response_format(
                        question_ids=[question.id for question in exam.questions],
                        authoritative_source_ids=authoritative_ids,
                    ),
                    max_tokens=_exam_review_token_budget(question_count),
                )
                validate_practice_exam_review(
                    review,
                    exam=exam,
                    authoritative_source_ids=authoritative_ids,
                    course_evidence=course_evidence,
                )
                await verify_open_answer_sheet(
                    self.model_client,
                    settings=settings,
                    exam=exam,
                    blind_review=review,
                    course_evidence=course_evidence,
                    authoritative_ids=authoritative_ids,
                )
                return exam
            except (ValidationError, PracticeExamValidationError) as exc:
                last_error = exc
                repair_error = str(exc)
                rejected_ids = getattr(exc, "question_ids", [])
                logger.warning(
                    "Practice exam candidate rejected; attempt=%s error_type=%s reason=%s",
                    attempt + 1,
                    type(exc).__name__,
                    _safe_validation_reason(exc),
                )
        detail = str(last_error) if last_error else "unknown validation error"
        raise PracticeExamPlanningError(
            f"Provider did not return a valid structured exam: {detail}"
        ) from last_error


def _exam_from_payload(
    payload: dict,
    *,
    course_id: str,
    language: str,
    duration_minutes: int,
    source_revision: str,
    ppi_source_ids: list[str],
) -> PracticeExam:
    questions = []
    failures: dict[str, str] = {}
    for item in payload["questions"]:
        try:
            questions.append(
                PracticeExamQuestion.model_validate(
                    {
                        **item,
                        **(
                            {"points": MULTIPLE_SELECT_POINTS}
                            if item.get("kind") == "multiple_select"
                            else {}
                        ),
                    }
                )
            )
        except ValidationError as exc:
            failures[item.get("id", "")] = str(exc)
    if failures:
        raise PracticeExamValidationError("; ".join(failures.values()), question_ids=list(failures))
    used_sources = sorted({source_id for item in questions for source_id in item.source_ids})
    return PracticeExam(
        id=uuid4().hex,
        course_id=course_id,
        title=payload["title"],
        language=language,
        instructions=sanitize_practice_exam_instructions(payload["instructions"]),
        duration_minutes=duration_minutes,
        created_at=datetime.now(UTC),
        total_points=sum(item.points for item in questions),
        source_revision=source_revision,
        source_ids=used_sources,
        ppi_source_ids=ppi_source_ids,
        questions=questions,
    )


def _source_revision(course_evidence: str, ppi_sources: dict[str, list[str]]) -> str:
    canonical = json.dumps(
        {"course": course_evidence, "ppi": ppi_sources}, sort_keys=True, ensure_ascii=False
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _exam_output_token_budget(question_count: int) -> int:
    return max(20_000, question_count * 600)


def _exam_review_token_budget(question_count: int) -> int:
    return max(12_000, question_count * 400)


def _safe_validation_reason(error: ValidationError | PracticeExamValidationError) -> str:
    if isinstance(error, PracticeExamValidationError):
        return str(error)
    return ",".join(sorted({item["type"] for item in error.errors()}))
