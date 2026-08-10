from __future__ import annotations

from pathlib import PurePosixPath

from lecturepilot.course_source_routing_models import CourseSourceRoute, SourceRouteRole
from lecturepilot.providers import ProviderConfigurationError


SUPPLEMENTAL_KINDS = {"code", "notebook", "python", "video"}
NON_TEACHING_MARKERS = {
    "assignment",
    "build",
    "exam",
    "feedback",
    "generated",
    "grading",
    "removed",
    "solution",
    "submission",
}


def require_supplemental_coverage(routes: list[CourseSourceRoute]) -> None:
    excluded = [
        route
        for route in routes
        if _is_supplemental_candidate(route) and route.role == SourceRouteRole.EXCLUDED
    ]
    if not excluded:
        return
    paths = ", ".join(sorted(route.path for route in excluded))
    raise ProviderConfigurationError(
        "The proposal excluded supplemental teaching material that must be assigned to its relevant "
        f"lecture instead of relying only on primary decks: {paths}"
    )


def _is_supplemental_candidate(route: CourseSourceRoute) -> bool:
    if route.kind.casefold() not in SUPPLEMENTAL_KINDS:
        return False
    words = {
        word
        for part in PurePosixPath(route.path.casefold()).parts
        for word in part.replace("_", "-").replace(".", "-").split("-")
    }
    return not words.intersection(NON_TEACHING_MARKERS)
