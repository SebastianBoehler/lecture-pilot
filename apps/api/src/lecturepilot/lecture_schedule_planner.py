from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from lecturepilot.agent_response_schema import lecture_schedule_response_format
from lecturepilot.course_canvas_json import parse_model_json
from lecturepilot.lecture_schedule_evidence import build_schedule_evidence
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_request_options import completion_options
from lecturepilot.model_usage import ModelUsageRecorder, complete_with_usage
from lecturepilot.models import (
    LectureScheduleItem,
    LectureScheduleProposal,
    ProviderCapability,
    ProviderSettings,
)
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry
from lecturepilot.source_bundle import SourceBundleFile


class LectureScheduleModelClient(Protocol):
    async def complete_schedule(
        self, *, settings: ProviderSettings, messages: list[dict[str, str]]
    ) -> dict:
        """Return a source-grounded full-course lecture schedule proposal."""


class LiteLLMScheduleClient:
    def __init__(self, usage_recorder: ModelUsageRecorder | None = None) -> None:
        self.usage_recorder = usage_recorder

    async def complete_schedule(
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
                response_format=lecture_schedule_response_format(),
                **completion_options(settings, temperature=0.1, max_tokens=8000),
            )
        except Exception as exc:
            raise ModelExecutionError("Lecture schedule model request failed.") from exc
        return parse_model_json(response.choices[0].message.content)


class LectureSchedulePlanner:
    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        model_client: LectureScheduleModelClient | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry.from_env()
        self.model_client = model_client or LiteLLMScheduleClient()

    async def propose_schedule(
        self,
        *,
        course_id: str,
        files: list[SourceBundleFile],
        roots: list[Path],
        first_lecture_date: date | None = None,
        requested_count: int | None = None,
    ) -> LectureScheduleProposal:
        settings = self.provider_registry.require_ready(
            [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        )
        messages = _schedule_messages(course_id, files, roots, first_lecture_date, requested_count)
        last_error: ProviderConfigurationError | None = None
        for _ in range(2):
            try:
                payload = await self.model_client.complete_schedule(
                    settings=settings, messages=messages
                )
                return _read_proposal(
                    payload,
                    course_id,
                    files,
                    requested_count=requested_count,
                )
            except ProviderConfigurationError as exc:
                last_error = exc
                messages = [*messages, _repair_message(str(exc))]
        raise last_error or ProviderConfigurationError(
            "Lecture schedule planner returned no usable proposal."
        )


def _schedule_messages(
    course_id: str,
    files: list[SourceBundleFile],
    roots: list[Path],
    first_lecture_date: date | None,
    requested_count: int | None,
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are the LecturePilot course-builder scheduling agent. Infer the "
                "course lecture structure from an uploaded source bundle. Use file names, "
                "directory relationships, LaTeX sections, Markdown headings, PDF text, text "
                "excerpts, and media metadata as evidence. Treat the complete inventory as "
                "authority; the selected excerpts are supporting evidence, not a complete "
                "file list. Infer lecture units semantically instead of requiring any naming "
                "pattern such as Lecture01. Distinguish primary teaching material from "
                "assignments, solutions, submissions, exam records, and generated artifacts. "
                "Return exactly one structured schedule with a top-level lectures "
                "array. Each lecture needs "
                "number, title, date, and material_path. Prefer concise real lecture topic "
                "titles over housekeeping frames such as plan, recap, feedback, note, or "
                "course thread. If a requested lecture count is absent, infer the count from "
                "the materials. Prefer explicit date cues from current-semester source files. "
                "When a requested lecture count is provided, return exactly that many rows. "
                "When dates are missing, use weekly dates starting from the provided first lecture date. "
                "Set material_path to null when no single source file belongs to the lecture."
            ),
        },
        {
            "role": "user",
            "content": _source_evidence(
                course_id, files, roots, first_lecture_date, requested_count
            ),
        },
    ]


def _repair_message(error: str) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            f"The previous schedule response violated the contract: {error}. "
            "Return exactly one structured schedule with this shape and no surrounding prose: "
            '{"lectures":[{"number":"01","title":"Topic title","date":"YYYY-MM-DD",'
            '"material_path":"Lecture01-eng.tex"}]}. Do not return a bare array.'
        ),
    }


_source_evidence = build_schedule_evidence


def _read_proposal(
    payload: dict,
    course_id: str,
    files: list[SourceBundleFile],
    requested_count: int | None = None,
) -> LectureScheduleProposal:
    raw_lectures = payload.get("lectures")
    if not isinstance(raw_lectures, list) or not raw_lectures:
        raise ProviderConfigurationError("Lecture schedule planner JSON must include lectures.")
    known_paths = {item.path for item in files}
    lectures: list[LectureScheduleItem] = []
    for index, raw in enumerate(raw_lectures[:80], start=1):
        if not isinstance(raw, dict):
            continue
        material_path = raw.get("material_path")
        if material_path is not None and (
            not isinstance(material_path, str) or material_path not in known_paths
        ):
            raise ProviderConfigurationError(
                "Lecture material_path must be null or an exact listed source path."
            )
        try:
            lectures.append(
                LectureScheduleItem(
                    number=_schedule_number(str(raw.get("number") or f"{index:02d}")),
                    title=str(raw.get("title") or f"Lecture {index:02d}"),
                    date=raw.get("date"),
                    material_path=material_path,
                )
            )
        except ValidationError as exc:
            raise ProviderConfigurationError(
                "Lecture schedule planner returned invalid lecture rows."
            ) from exc
    if not lectures:
        raise ProviderConfigurationError("Lecture schedule planner returned no usable lectures.")
    numbers = [lecture.number for lecture in lectures]
    if len(set(numbers)) != len(numbers):
        raise ProviderConfigurationError("Every schedule row needs a unique lecture number.")
    if requested_count is not None and len(lectures) != requested_count:
        raise ProviderConfigurationError(
            "Lecture schedule planner must return the requested lecture count."
        )
    return LectureScheduleProposal(
        course_id=course_id,
        lectures=lectures,
        source_paths=[lecture.material_path for lecture in lectures if lecture.material_path],
    )


def _schedule_number(number: str) -> str:
    import re

    digits = re.sub(r"\D+", "", number)
    return f"{int(digits):02d}" if digits else number.strip()
