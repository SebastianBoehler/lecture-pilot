from __future__ import annotations

from typing import Protocol
from lecturepilot.agent_response_schema import course_canvas_section_response_format

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.course_canvas_approved_checkpoints import assemble_approved_checkpoints
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_math import validate_section_math
from lecturepilot.course_canvas_practice_contract import (
    practice_source_sections,
    section_target_assignments,
    validate_section_practice,
)
from lecturepilot.course_canvas_section_reader import read_section_payload as _read_section_payload
from lecturepilot.course_canvas_section_batch import SectionPlanResult, plan_section_batch
from lecturepilot.course_canvas_section_checkpoints import (
    SectionPlanCheckpointStore,
    current_section_plan_checkpoint_store,
)
from lecturepilot.course_canvas_section_prompt import section_messages as _section_messages
from lecturepilot.course_canvas_section_values import allowed_assets as _allowed_assets
from lecturepilot.course_canvas_validation import validate_section_assessments
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.models import ProviderSettings
from lecturepilot.observability import Observability
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.course_practice_design_models import PracticeDesign, PracticeTarget


SECTION_PLAN_ATTEMPTS = 2


class SectionPlanModelClient(Protocol):
    async def complete_plan(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
        response_format: dict | None = None,
    ) -> dict:
        """Return one section-level canvas plan."""


async def plan_sections_individually(
    *,
    model_client: SectionPlanModelClient,
    settings: ProviderSettings,
    source_document: CanvasDocument,
    practice_design: PracticeDesign,
    output_language: str = "en",
    repair_context: str | None = None,
    observability: Observability | None = None,
    span_attributes: dict[str, str] | None = None,
    checkpoint_store: SectionPlanCheckpointStore | None = None,
) -> CanvasDocument:
    checkpoint_store = checkpoint_store or current_section_plan_checkpoint_store()
    source_sections = practice_source_sections(source_document)
    if not source_sections:
        raise CanvasGenerationRepairableError("Section planner returned no usable sections.")
    trace = observability or Observability()
    assignments = section_target_assignments(practice_design, source_sections)

    async def plan_one(section_index: int, source_section: CanvasSection) -> SectionPlanResult:
        if checkpoint_store is not None:
            cached = checkpoint_store.read(
                source_section,
                model=settings.model,
                output_language=output_language,
                practice_design_revision=practice_design.revision,
            )
            if cached is not None:
                try:
                    validate_section_practice(cached, assignments[source_section.id])
                except CanvasGenerationRepairableError:
                    pass  # An incomplete section is not a reusable generation checkpoint.
                else:
                    return SectionPlanResult(cached)
        result = await _plan_section(
            model_client=model_client,
            settings=settings,
            source_document=source_document,
            source_section=source_section,
            applicable_targets=assignments[source_section.id],
            practice_design=practice_design,
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
                practice_design_revision=practice_design.revision,
            )
        return result

    return await plan_section_batch(source_document, source_sections, plan_one)


async def _plan_section(
    *,
    model_client: SectionPlanModelClient,
    settings: ProviderSettings,
    source_document: CanvasDocument,
    source_section: CanvasSection,
    practice_design: PracticeDesign,
    applicable_targets: tuple[PracticeTarget, ...],
    output_language: str,
    repair_context: str | None,
    observability: Observability,
    span_attributes: dict[str, str],
    section_index: int,
) -> SectionPlanResult:
    messages = _section_messages(
        source_document,
        source_section,
        practice_design=practice_design,
        applicable_targets=applicable_targets,
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
                payload = await model_client.complete_plan(
                    settings=settings,
                    messages=messages,
                    response_format=course_canvas_section_response_format(),
                )
                section = _read_section_payload(
                    payload,
                    source_section,
                    allowed_assets,
                    output_language=output_language,
                    require_checkpoint=not applicable_targets,
                )
                section = assemble_approved_checkpoints(section, applicable_targets)
                validate_section_math(section)
                validate_section_practice(section, applicable_targets)
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
