from __future__ import annotations

from pathlib import Path, PurePosixPath
from lecturepilot.course_source_evidence import selection_detail_files, source_file_excerpt
from lecturepilot.course_source_routing_client import (
    LiteLLMSourceRoutingClient,
    SourceRoutingModelClient,
)
from lecturepilot.course_source_routing_models import CourseSourceRoute, SourceRouteRole
from lecturepilot.course_source_routing_quality import require_supplemental_coverage
from lecturepilot.course_source_routing_review import (
    apply_review_corrections,
    routing_review_messages,
)
from lecturepilot.models import Lecture, ProviderCapability, ProviderSettings
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_provider_errors import is_retryable_provider_error
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry
from lecturepilot.source_index_models import IndexedSourceFile


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
        ordered = await self._propose_selection(
            settings=settings,
            messages=_routing_messages(course_id, files, lectures, roots),
            files=files,
            lectures=lectures,
        )
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
        last_error: ProviderConfigurationError | ModelExecutionError | None = None
        for _ in range(3):
            try:
                payload = await self.model_client.review_routing(
                    settings=settings, messages=messages
                )
                reviewed = apply_review_corrections(
                    payload,
                    routes,
                    lectures,
                    protected_paths=_primary_paths(lectures),
                )
                require_supplemental_coverage(reviewed)
                return reviewed
            except (ProviderConfigurationError, ModelExecutionError) as exc:
                last_error = exc
                if (
                    isinstance(exc, ModelExecutionError)
                    and exc.__cause__ is not None
                    and not is_retryable_provider_error(exc.__cause__)
                ):
                    raise
                messages = [*messages, _review_repair_message(str(exc))]
        raise last_error or ProviderConfigurationError(
            "Source-routing review agent returned no usable corrections."
        )

    async def _propose_selection(
        self,
        *,
        settings: ProviderSettings,
        messages: list[dict[str, str]],
        files: list[IndexedSourceFile],
        lectures: list[Lecture],
    ) -> list[CourseSourceRoute]:
        last_error: ProviderConfigurationError | ModelExecutionError | None = None
        for _ in range(3):
            try:
                payload = await self.model_client.complete_routing(
                    settings=settings, messages=messages
                )
                routes = _read_selected_routes(payload, files, lectures)
                require_supplemental_coverage(routes)
                return routes
            except (ProviderConfigurationError, ModelExecutionError) as exc:
                last_error = exc
                if (
                    isinstance(exc, ModelExecutionError)
                    and exc.__cause__ is not None
                    and not is_retryable_provider_error(exc.__cause__)
                ):
                    raise
                messages = [*messages, _repair_message(str(exc))]
        raise last_error or ProviderConfigurationError(
            "Source-routing agent returned no usable selection."
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
                "You are the LecturePilot source-selection agent. The professor-reviewed lecture "
                "schedule already identifies each lecture's authoritative primary source. Return "
                "only additional selected sources that are genuinely needed for one lecture or "
                "the whole course; all omitted files stay excluded. Infer semantically from content "
                "and hierarchy without requiring a naming or folder convention. Never select "
                "assignment sheets, assignment slides, submissions, solutions, answer keys, grading "
                "material, exam-preparation guidance, exam protocols, temporary artifacts, or derived "
                "text conversions when an original is present. Use course_wide only for foundational "
                "teaching material applicable to every lecture, such as a syllabus or shared glossary. "
                "Do not assume the primary deck supersedes complementary examples, code demos, "
                "readings, or standalone diagrams; select them when they add teaching evidence or "
                "reusable media beyond the rendered deck. Exclude generated slide-page images and "
                "individual deck assets when they merely duplicate a selected deck. "
                "Every listed notebook, code demo, or video that is not an assignment, solution, "
                "submission, or generated artifact is supplemental teaching material: select it "
                "for the most relevant lecture instead of omitting it. "
                "Do not return a primary source again. Use only listed paths and lecture ids. Lecture "
                "selections require lecture_id; course_wide selections require null."
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
    lines.append(f"\nComplete course inventory ({len(files)} files):")
    for item in files:
        lines.append(f"- path={item.path}; kind={item.kind}; size={item.size_bytes}")
    details = selection_detail_files(files, _primary_paths(lectures))
    lines.append(f"\nCandidate content evidence ({len(details)} representative files):")
    for item in details:
        lines.append(
            f"- path={item.path}; kind={item.kind}; size={item.size_bytes}\n"
            f"  content={source_file_excerpt(item, roots)}"
        )
    return "\n".join(lines)


def _read_selected_routes(
    payload: dict, files: list[IndexedSourceFile], lectures: list[Lecture]
) -> list[CourseSourceRoute]:
    raw_routes = payload.get("selections") if isinstance(payload, dict) else None
    if not isinstance(raw_routes, list):
        raise ProviderConfigurationError("Source-routing JSON must include a selections array.")
    indexed = {item.path: item for item in files}
    lecture_ids = {lecture.id for lecture in lectures}
    primary = {
        lecture.material_path: lecture.id
        for lecture in lectures
        if lecture.material_path is not None
    }
    parsed: dict[str, CourseSourceRoute] = {}
    for raw in raw_routes:
        if not isinstance(raw, dict) or not isinstance(raw.get("path"), str):
            raise ProviderConfigurationError("Every source route needs an exact path.")
        path = _resolve_selected_path(raw["path"], indexed)
        if path in primary:
            raise ProviderConfigurationError(
                f"Do not reselect professor-reviewed primary source: {path}"
            )
        try:
            role = SourceRouteRole(raw.get("role"))
        except ValueError as exc:
            raise ProviderConfigurationError("Use a supported source-routing role.") from exc
        if role == SourceRouteRole.EXCLUDED:
            raise ProviderConfigurationError("Omit excluded sources from the selection.")
        lecture_id = raw.get("lecture_id")
        if role == SourceRouteRole.LECTURE and lecture_id not in lecture_ids:
            raise ProviderConfigurationError("Lecture routes must use a known lecture id.")
        if role != SourceRouteRole.LECTURE and lecture_id is not None:
            raise ProviderConfigurationError("Only lecture routes may include a lecture id.")
        item = indexed[path]
        route = CourseSourceRoute(
            path=path,
            kind=item.kind,
            sha256=item.sha256,
            role=role,
            lecture_id=lecture_id,
        )
        if path in parsed:
            if parsed[path] == route:
                continue
            raise ProviderConfigurationError(f"Duplicate source path returned: {path}")
        parsed[path] = route
    routes = []
    for item in files:
        routes.append(
            parsed.get(item.path)
            or CourseSourceRoute(
                path=item.path,
                kind=item.kind,
                sha256=item.sha256,
                role=(
                    SourceRouteRole.LECTURE if item.path in primary else SourceRouteRole.EXCLUDED
                ),
                lecture_id=primary.get(item.path),
            )
        )
    return routes


def _repair_message(error: str) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            f"The proposal violated the routing contract: {error} "
            "Return a lecture or course_wide selection for every listed path in the error; do not "
            "omit any of those required teaching sources."
        ),
    }


def _review_repair_message(error: str) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            f"The global review violated the correction contract: {error} "
            "Return a lecture or course_wide correction for every listed path in the error; do not "
            "leave any of those required teaching sources excluded."
        ),
    }


def _primary_paths(lectures: list[Lecture]) -> set[str]:
    return {lecture.material_path for lecture in lectures if lecture.material_path}


def _resolve_selected_path(returned_path: str, indexed: dict[str, IndexedSourceFile]) -> str:
    if returned_path in indexed:
        return returned_path
    filename = PurePosixPath(returned_path).name
    matches = [path for path in indexed if PurePosixPath(path).name == filename]
    if len(matches) == 1:
        return matches[0]
    raise ProviderConfigurationError(f"Unknown source path returned: {returned_path}")
