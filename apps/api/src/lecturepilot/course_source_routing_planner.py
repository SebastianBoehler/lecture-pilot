from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from lecturepilot.agent_response_schema import source_routing_response_format
from lecturepilot.course_canvas_json import parse_model_json
from lecturepilot.course_source_routing_models import CourseSourceRoute, SourceRouteRole
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_request_options import completion_options
from lecturepilot.model_usage import ModelUsageRecorder, complete_with_usage
from lecturepilot.models import Lecture, ProviderCapability, ProviderSettings
from lecturepilot.pdf_extract import read_pdf_text
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry
from lecturepilot.source_index_models import IndexedSourceFile


MAX_FILES_PER_REQUEST = 50
MAX_EXCERPT_CHARS = 900
TEXT_KINDS = {"json", "latex", "markdown", "notebook", "python", "text"}


class SourceRoutingModelClient(Protocol):
    async def complete_routing(
        self, *, settings: ProviderSettings, messages: list[dict[str, str]]
    ) -> dict:
        """Return one validated source assignment per listed file."""


class LiteLLMSourceRoutingClient:
    def __init__(self, usage_recorder: ModelUsageRecorder | None = None) -> None:
        self.usage_recorder = usage_recorder

    async def complete_routing(
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
                response_format=source_routing_response_format(),
                **completion_options(settings, temperature=0.1, max_tokens=8000),
            )
        except Exception as exc:
            raise ModelExecutionError("Source-routing model request failed.") from exc
        return parse_model_json(response.choices[0].message.content)


class CourseSourceRoutingPlanner:
    def __init__(
        self,
        provider_registry: ProviderRegistry | None = None,
        model_client: SourceRoutingModelClient | None = None,
    ) -> None:
        self.provider_registry = provider_registry or ProviderRegistry.from_env()
        self.model_client = model_client or LiteLLMSourceRoutingClient()

    async def propose_routes(
        self,
        *,
        course_id: str,
        files: list[IndexedSourceFile],
        lectures: list[Lecture],
        roots: list[Path],
    ) -> list[CourseSourceRoute]:
        if not files:
            return []
        settings = self.provider_registry.require_ready(
            [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
        )
        proposed: dict[str, CourseSourceRoute] = {}
        for offset in range(0, len(files), MAX_FILES_PER_REQUEST):
            batch = files[offset : offset + MAX_FILES_PER_REQUEST]
            routes = await self._propose_batch(
                settings=settings,
                messages=_routing_messages(course_id, batch, lectures, roots),
                files=batch,
                lectures=lectures,
            )
            proposed.update({route.path: route for route in routes})
        return [proposed[item.path] for item in files]

    async def _propose_batch(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
        files: list[IndexedSourceFile],
        lectures: list[Lecture],
    ) -> list[CourseSourceRoute]:
        last_error: ProviderConfigurationError | None = None
        for _ in range(2):
            try:
                payload = await self.model_client.complete_routing(
                    settings=settings, messages=messages
                )
                return _read_routes(payload, files, lectures)
            except ProviderConfigurationError as exc:
                last_error = exc
                messages = [*messages, _repair_message(str(exc))]
        raise last_error or ProviderConfigurationError(
            "Source-routing agent returned no usable assignments."
        )


def _routing_messages(
    course_id: str,
    files: list[IndexedSourceFile],
    lectures: list[Lecture],
    roots: list[Path],
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are the LecturePilot source-routing agent. Semantically assign every "
                "listed file exactly once before a professor reviews the proposal. Use lecture "
                "for material needed by one lecture, course_wide for material needed by every "
                "lecture, and excluded only when a file must never enter Canvas generation "
                "because it is unrelated, a build artifact, a submission, an answer key, or a "
                "duplicate. Do not exclude a file merely because its name is ambiguous; inspect "
                "its content evidence and choose the best lecture. Use only the listed paths and "
                "lecture ids. A lecture route requires lecture_id; other roles require null."
            ),
        },
        {
            "role": "user",
            "content": _routing_evidence(course_id, files, lectures, roots),
        },
    ]


def _routing_evidence(
    course_id: str,
    files: list[IndexedSourceFile],
    lectures: list[Lecture],
    roots: list[Path],
) -> str:
    lines = [f"Course id: {course_id}", "Lectures:"]
    for lecture in lectures:
        lines.append(
            f"- id={lecture.id}; title={lecture.title}; date={lecture.date}; "
            f"primary_path={lecture.material_path or 'none'}"
        )
    lines.append("\nFiles to assign exactly once:")
    for item in files:
        lines.append(
            f"- path={item.path}; kind={item.kind}; size={item.size_bytes}\n"
            f"  content={_file_excerpt(item, roots)}"
        )
    return "\n".join(lines)


def _file_excerpt(item: IndexedSourceFile, roots: list[Path]) -> str:
    path = _resolve_source(item.path, roots)
    if path is None:
        return "file contents unavailable"
    try:
        if item.kind == "pdf":
            return _compact(read_pdf_text(str(path), max_pages=3, max_chars=MAX_EXCERPT_CHARS))
        if item.kind in TEXT_KINDS:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                return _compact(handle.read(MAX_EXCERPT_CHARS * 2))
    except (OSError, RuntimeError, ValueError):
        return "text extraction unavailable; use path and file metadata"
    return "binary asset; use path and surrounding course structure"


def _read_routes(
    payload: dict, files: list[IndexedSourceFile], lectures: list[Lecture]
) -> list[CourseSourceRoute]:
    raw_routes = payload.get("routes") if isinstance(payload, dict) else None
    if not isinstance(raw_routes, list):
        raise ProviderConfigurationError("Source-routing JSON must include a routes array.")
    indexed = {item.path: item for item in files}
    lecture_ids = {lecture.id for lecture in lectures}
    parsed: dict[str, CourseSourceRoute] = {}
    for raw in raw_routes:
        if not isinstance(raw, dict) or not isinstance(raw.get("path"), str):
            raise ProviderConfigurationError("Every source route needs an exact path.")
        path = raw["path"]
        if path not in indexed or path in parsed:
            raise ProviderConfigurationError("Use every listed source path exactly once.")
        try:
            role = SourceRouteRole(raw.get("role"))
        except ValueError as exc:
            raise ProviderConfigurationError("Use a supported source-routing role.") from exc
        lecture_id = raw.get("lecture_id")
        if role == SourceRouteRole.LECTURE and lecture_id not in lecture_ids:
            raise ProviderConfigurationError("Lecture routes must use a known lecture id.")
        if role != SourceRouteRole.LECTURE and lecture_id is not None:
            raise ProviderConfigurationError("Only lecture routes may include a lecture id.")
        item = indexed[path]
        parsed[path] = CourseSourceRoute(
            path=path,
            kind=item.kind,
            sha256=item.sha256,
            role=role,
            lecture_id=lecture_id,
        )
    if parsed.keys() != indexed.keys():
        raise ProviderConfigurationError("Assign every listed path exactly once.")
    return [parsed[item.path] for item in files]


def _repair_message(error: str) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            f"The proposal violated the routing contract: {error} "
            "Assign every listed path exactly once using only lecture, course_wide, or excluded."
        ),
    }


def _resolve_source(relative_path: str, roots: list[Path]) -> Path | None:
    for root in roots:
        candidate = root / relative_path
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()[:MAX_EXCERPT_CHARS] or "no text extracted"
