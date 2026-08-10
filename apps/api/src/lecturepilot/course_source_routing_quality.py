from __future__ import annotations

from pathlib import PurePosixPath

from lecturepilot.course_source_routing_models import CourseSourceRoute, SourceRouteRole
from lecturepilot.providers import ProviderConfigurationError


SUPPLEMENTAL_KINDS = {"code", "notebook", "video"}
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
    candidates = [route for route in routes if _is_supplemental_candidate(route)]
    if not candidates:
        return
    if any(route.role != SourceRouteRole.EXCLUDED for route in candidates):
        return
    raise ProviderConfigurationError(
        "The proposal excluded every supplemental teaching material candidate. Select relevant "
        "code demos, notebooks, or videos for their lecture instead of relying only on primary decks."
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
