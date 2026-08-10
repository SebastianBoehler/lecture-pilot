import pytest

from lecturepilot.course_source_routing_models import CourseSourceRoute, SourceRouteRole
from lecturepilot.course_source_routing_quality import require_supplemental_coverage
from lecturepilot.providers import ProviderConfigurationError


def test_primary_only_proposal_is_rejected_when_supplemental_material_exists() -> None:
    routes = [
        _route("Lecture01.pdf", "pdf", SourceRouteRole.LECTURE, "lecture-01"),
        _route("code/regression-demo.ipynb", "notebook", SourceRouteRole.EXCLUDED),
        _route("videos/ridge-demo.mp4", "video", SourceRouteRole.EXCLUDED),
    ]

    with pytest.raises(ProviderConfigurationError, match="supplemental teaching material"):
        require_supplemental_coverage(routes)


def test_proposal_passes_when_at_least_one_supplemental_source_is_assigned() -> None:
    routes = [
        _route("Lecture01.pdf", "pdf", SourceRouteRole.LECTURE, "lecture-01"),
        _route("code/regression-demo.ipynb", "notebook", SourceRouteRole.LECTURE, "lecture-01"),
        _route("videos/unrelated.mp4", "video", SourceRouteRole.EXCLUDED),
    ]

    require_supplemental_coverage(routes)


def test_non_teaching_artifacts_do_not_force_supplemental_assignment() -> None:
    routes = [
        _route("Lecture01.pdf", "pdf", SourceRouteRole.LECTURE, "lecture-01"),
        _route("feedback/assignment-solution.ipynb", "notebook", SourceRouteRole.EXCLUDED),
    ]

    require_supplemental_coverage(routes)


def _route(
    path: str,
    kind: str,
    role: SourceRouteRole,
    lecture_id: str | None = None,
) -> CourseSourceRoute:
    return CourseSourceRoute(
        path=path,
        kind=kind,
        sha256="a" * 64,
        role=role,
        lecture_id=lecture_id,
    )
