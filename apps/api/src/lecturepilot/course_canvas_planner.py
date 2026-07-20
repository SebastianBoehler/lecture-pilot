from __future__ import annotations

from typing import Protocol
from uuid import uuid4

from lecturepilot.agent_response_schema import course_canvas_response_format
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_content_filter import filter_source_document_for_planning
from lecturepilot.course_canvas_enrichment import enrich_learning_document
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_json import parse_model_json
from lecturepilot.course_canvas_section_planner import plan_sections_individually
from lecturepilot.course_canvas_section_repair import CourseCanvasSectionRepairMixin
from lecturepilot.course_canvas_validation import validate_planned_document
from lecturepilot.course_slide_interleaving import interleave_original_slides
from lecturepilot.course_planner_warnings import planned_payload
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_request_options import completion_options
from lecturepilot.model_usage import ModelUsageRecorder, complete_with_usage
from lecturepilot.models import ProviderCapability, ProviderSettings
from lecturepilot.observability import Observability
from lecturepilot.logging_observability import current_operation_id
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry


class CoursePlanModelClient(Protocol):
    async def complete_plan(
        self, *, settings: ProviderSettings, messages: list[dict[str, str]]
    ) -> dict:
        """Return one source-grounded course canvas plan."""


class LiteLLMCoursePlanClient:
    def __init__(self, usage_recorder: ModelUsageRecorder | None = None) -> None:
        self.usage_recorder = usage_recorder

    async def complete_plan(
        self, *, settings: ProviderSettings, messages: list[dict[str, str]]
    ) -> dict:
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
                messages=messages,
                response_format=course_canvas_response_format(),
                **completion_options(settings, temperature=0.2, max_tokens=6000),
            )
        except Exception as exc:
            raise ModelExecutionError("Course planner model request failed.") from exc
        content = response.choices[0].message.content
        finish_reason = str(getattr(response.choices[0], "finish_reason", "") or "")
        return planned_payload(parse_model_json(content), finish_reason=finish_reason)


class CourseCanvasPlanner(CourseCanvasSectionRepairMixin):
    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        model_client: CoursePlanModelClient | None = None,
        observability: Observability | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry.from_env()
        self.model_client = model_client or LiteLLMCoursePlanClient()
        self.observability = observability or Observability()

    async def plan_canvas(
        self,
        source_document: CanvasDocument,
        *,
        repair_context: str | None = None,
        output_language: str = "en",
    ) -> CanvasDocument:
        settings = self.provider_registry.require_ready(
            [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        )
        source_document = filter_source_document_for_planning(source_document)
        generation_id = current_operation_id() or uuid4().hex
        span_attributes = {
            "course_id": source_document.course_id,
            "lecture_id": source_document.lecture_id,
            "generation_id": generation_id,
            "provider": settings.provider,
            "model": settings.model,
        }
        document: CanvasDocument | None = None
        try:
            with self.observability.model_span(
                stage="sectionwise_plan", attempt=1, **span_attributes
            ) as span:
                document = await plan_sections_individually(
                    model_client=self.model_client,
                    settings=settings,
                    source_document=source_document,
                    output_language=output_language,
                    repair_context=repair_context,
                    observability=self.observability,
                    span_attributes=span_attributes,
                )
                document = enrich_learning_document(document, output_language=output_language)
                document = interleave_original_slides(document, source_document)
                validate_planned_document(document, source_document)
                span.set_outputs(
                    {
                        "section_count": len(document.sections),
                        "warning_count": len(document.warnings),
                    }
                )
                return document
        except CanvasGenerationRepairableError as exc:
            candidate = exc.candidate or document
            if candidate is not None:
                candidate = enrich_learning_document(candidate, output_language=output_language)
                candidate = interleave_original_slides(candidate, source_document)
                exc.with_candidate(candidate)
            raise
