from __future__ import annotations

from pathlib import Path

from lecturepilot.course_source_evidence import source_file_excerpt
from lecturepilot.course_source_routing_models import CourseSourceRoute, SourceRouteRole
from lecturepilot.models import Lecture
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.source_index_models import IndexedSourceFile


def routing_review_messages(
    course_id: str,
    files: list[IndexedSourceFile],
    lectures: list[Lecture],
    roots: list[Path],
    routes: list[CourseSourceRoute],
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are the global LecturePilot source-routing reviewer. Review the complete "
                "least-privilege proposal before a professor sees it. Return only corrections. "
                "Judge files semantically from their content, hierarchy, the full manifest, and "
                "the lecture plan; never require a naming convention. Exclude student submissions, "
                "assignments when primary teaching material exists, answer keys, grading material, "
                "exam-preparation guidance, exam protocols, temporary artifacts, and derived copies "
                "when their original source is present and readable. Reserve course_wide for "
                "foundational teaching material applicable to every lecture, such as a syllabus or "
                "shared glossary. Ensure relevant complementary examples, code demos, readings, and "
                "standalone diagrams are not excluded merely because a primary deck exists. Keep "
                "generated slide-page images and individual deck assets excluded when they duplicate "
                "that deck. Keep project metadata such as pyproject.toml excluded; it is not a "
                "teaching code demo. A professor can assign it later when environment setup is "
                "itself taught. Never exclude a listed notebook, code demo, or video unless it is an "
                "assignment, solution, submission, or generated artifact; otherwise route it to the "
                "most relevant lecture. Ensure each lecture keeps its authoritative teaching material. Use "
                "only listed paths and lecture ids. Lecture corrections require a lecture_id; "
                "course_wide and excluded corrections require null. An empty corrections array means "
                "the complete proposal is semantically coherent. The professor remains the final "
                "authority."
            ),
        },
        {
            "role": "user",
            "content": _review_evidence(course_id, files, lectures, roots, routes),
        },
    ]


def _review_evidence(
    course_id: str,
    files: list[IndexedSourceFile],
    lectures: list[Lecture],
    roots: list[Path],
    routes: list[CourseSourceRoute],
) -> str:
    indexed = {item.path: item for item in files}
    primary_paths = {lecture.material_path for lecture in lectures if lecture.material_path}
    lines = [f"Course id: {course_id}", "Lectures:"]
    for lecture in lectures:
        lines.append(
            f"- id={lecture.id}; title={lecture.title}; primary_path={lecture.material_path or 'none'}"
        )
    lines.append(f"\nComplete proposed manifest ({len(routes)} files):")
    for route in routes:
        lines.append(
            f"- path={route.path}; kind={route.kind}; role={route.role.value}; "
            f"lecture_id={route.lecture_id or 'null'}"
        )
    side_routes = [
        route
        for route in routes
        if route.role != SourceRouteRole.EXCLUDED and route.path not in primary_paths
    ]
    lines.append(f"\nContent evidence for selected non-primary sources ({len(side_routes)} files):")
    for route in side_routes:
        item = indexed[route.path]
        lines.append(f"- path={route.path}\n  content={source_file_excerpt(item, roots)}")
    return "\n".join(lines)


def apply_review_corrections(
    payload: dict,
    routes: list[CourseSourceRoute],
    lectures: list[Lecture],
    *,
    protected_paths: set[str] | None = None,
) -> list[CourseSourceRoute]:
    raw_corrections = payload.get("corrections") if isinstance(payload, dict) else None
    if not isinstance(raw_corrections, list):
        raise ProviderConfigurationError(
            "Source-routing review JSON must include a corrections array."
        )
    current = {route.path: route for route in routes}
    lecture_ids = {lecture.id for lecture in lectures}
    seen: set[str] = set()
    for raw in raw_corrections:
        if not isinstance(raw, dict) or not isinstance(raw.get("path"), str):
            raise ProviderConfigurationError("Every correction needs an exact path.")
        path = raw["path"]
        if path not in current:
            raise ProviderConfigurationError(f"Unknown correction path returned: {path}")
        if path in seen:
            raise ProviderConfigurationError(f"Duplicate correction path returned: {path}")
        if path in (protected_paths or set()):
            raise ProviderConfigurationError(
                f"Do not change professor-reviewed primary source: {path}"
            )
        seen.add(path)
        try:
            role = SourceRouteRole(raw.get("role"))
        except ValueError as exc:
            raise ProviderConfigurationError("Use a supported source-routing role.") from exc
        lecture_id = raw.get("lecture_id")
        if role == SourceRouteRole.LECTURE and lecture_id not in lecture_ids:
            raise ProviderConfigurationError("Lecture corrections must use a known lecture id.")
        if role != SourceRouteRole.LECTURE and lecture_id is not None:
            raise ProviderConfigurationError("Only lecture corrections may include a lecture id.")
        original = current[path]
        current[path] = original.model_copy(update={"role": role, "lecture_id": lecture_id})
    return [current[route.path] for route in routes]
