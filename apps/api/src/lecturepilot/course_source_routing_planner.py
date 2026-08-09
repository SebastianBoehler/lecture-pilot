from __future__ import annotations

from pathlib import Path
from lecturepilot.course_source_evidence import source_file_excerpt
from lecturepilot.course_source_routing_client import (
    LiteLLMSourceRoutingClient,
    SourceRoutingModelClient,
)
from lecturepilot.course_source_routing_models import CourseSourceRoute, SourceRouteRole
from lecturepilot.course_source_routing_review import (
    apply_review_corrections,
    routing_review_messages,
)
from lecturepilot.models import Lecture, ProviderCapability, ProviderSettings
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry
from lecturepilot.source_index_models import IndexedSourceFile


MAX_FILES_PER_REQUEST = 24


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
        for batch in source_route_batches(files):
            routes = await self._propose_batch(
                settings=settings,
                messages=_routing_messages(course_id, batch, lectures, roots, inventory=files),
                files=batch,
                lectures=lectures,
            )
            proposed.update({route.path: route for route in routes})
        ordered = [proposed[item.path] for item in files]
        return await self._review_complete_manifest(
            settings=settings,
            messages=routing_review_messages(course_id, files, lectures, roots, ordered),
            routes=ordered,
            lectures=lectures,
        )

    async def _review_complete_manifest(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
        routes: list[CourseSourceRoute],
        lectures: list[Lecture],
    ) -> list[CourseSourceRoute]:
        last_error: ProviderConfigurationError | None = None
        for _ in range(2):
            try:
                payload = await self.model_client.review_routing(
                    settings=settings, messages=messages
                )
                return apply_review_corrections(payload, routes, lectures)
            except ProviderConfigurationError as exc:
                last_error = exc
                messages = [*messages, _review_repair_message(str(exc))]
        raise last_error or ProviderConfigurationError(
            "Source-routing review agent returned no usable corrections."
        )

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


def source_route_batches(files: list[IndexedSourceFile]) -> list[list[IndexedSourceFile]]:
    return [
        files[offset : offset + MAX_FILES_PER_REQUEST]
        for offset in range(0, len(files), MAX_FILES_PER_REQUEST)
    ]


def _routing_messages(
    course_id: str,
    files: list[IndexedSourceFile],
    lectures: list[Lecture],
    roots: list[Path],
    *,
    inventory: list[IndexedSourceFile],
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
                "lecture ids. Treat derived conversions as duplicates when the inventory contains "
                "their original source. Student submissions, answer keys, grading schemes, and "
                "temporary render artifacts must be excluded. When primary lecture material exists, "
                "exclude assignment sheets, assignment slides, graded reports, and derived text "
                "conversions of those artifacts; they must not shape the lecture Canvas. Also exclude "
                "derived text conversions of primary PDFs when the original PDF is present and "
                "readable. A lecture route requires lecture_id; other roles require null."
            ),
        },
        {
            "role": "user",
            "content": _routing_evidence(course_id, files, lectures, roots, inventory=inventory),
        },
    ]


def _routing_evidence(
    course_id: str,
    files: list[IndexedSourceFile],
    lectures: list[Lecture],
    roots: list[Path],
    *,
    inventory: list[IndexedSourceFile],
) -> str:
    lines = [f"Course id: {course_id}", "Lectures:"]
    for lecture in lectures:
        lines.append(
            f"- id={lecture.id}; title={lecture.title}; date={lecture.date}; "
            f"primary_path={lecture.material_path or 'none'}"
        )
    lines.append(f"\nComplete course inventory ({len(inventory)} files), for context only:")
    for item in inventory:
        lines.append(f"- path={item.path}; kind={item.kind}; size={item.size_bytes}")
    noun = "file" if len(files) == 1 else "files"
    lines.append(f"\nFiles to assign in this response ({len(files)} {noun}), exactly once:")
    for item in files:
        lines.append(
            f"- path={item.path}; kind={item.kind}; size={item.size_bytes}\n"
            f"  content={source_file_excerpt(item, roots)}"
        )
    return "\n".join(lines)


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
        if path not in indexed:
            raise ProviderConfigurationError(f"Unknown source path returned: {path}")
        if path in parsed:
            raise ProviderConfigurationError(f"Duplicate source path returned: {path}")
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
        missing = [item.path for item in files if item.path not in parsed]
        raise ProviderConfigurationError(
            "Assign every listed path exactly once. Missing paths: " + ", ".join(missing)
        )
    return [parsed[item.path] for item in files]


def _repair_message(error: str) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            f"The proposal violated the routing contract: {error} "
            "Assign every listed path exactly once using only lecture, course_wide, or excluded."
        ),
    }


def _review_repair_message(error: str) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            f"The global review violated the correction contract: {error} "
            "Return only unique corrections for listed paths."
        ),
    }
