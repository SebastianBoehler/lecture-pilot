from datetime import date

import pytest

from lecturepilot.course_source_routing_planner import CourseSourceRoutingPlanner
from lecturepilot.course_source_routing_models import CourseSourceRoute, SourceRouteRole
from lecturepilot.course_source_routing_quality import require_supplemental_coverage
from lecturepilot.models import Lecture
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry
from lecturepilot.source_index_models import IndexedSourceFile


def test_primary_only_proposal_is_rejected_when_supplemental_material_exists() -> None:
    routes = [
        _route("Lecture01.pdf", "pdf", SourceRouteRole.LECTURE, "lecture-01"),
        _route("code/regression-demo.ipynb", "notebook", SourceRouteRole.EXCLUDED),
        _route("videos/ridge-demo.mp4", "video", SourceRouteRole.EXCLUDED),
    ]

    with pytest.raises(ProviderConfigurationError, match="supplemental teaching material"):
        require_supplemental_coverage(routes)


def test_proposal_is_rejected_when_any_supplemental_source_is_unassigned() -> None:
    routes = [
        _route("Lecture01.pdf", "pdf", SourceRouteRole.LECTURE, "lecture-01"),
        _route("code/regression-demo.ipynb", "notebook", SourceRouteRole.LECTURE, "lecture-01"),
        _route("videos/ridge-demo.mp4", "video", SourceRouteRole.EXCLUDED),
    ]

    with pytest.raises(ProviderConfigurationError, match="videos/ridge-demo.mp4"):
        require_supplemental_coverage(routes)


def test_non_teaching_artifacts_do_not_force_supplemental_assignment() -> None:
    routes = [
        _route("Lecture01.pdf", "pdf", SourceRouteRole.LECTURE, "lecture-01"),
        _route("feedback/assignment-solution.ipynb", "notebook", SourceRouteRole.EXCLUDED),
    ]

    require_supplemental_coverage(routes)


@pytest.mark.asyncio
async def test_planner_repairs_a_primary_only_model_response(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_MODEL", "openai/gpt-5.6-luna")
    monkeypatch.setenv("LECTUREPILOT_ALLOWED_MODELS", "openai/gpt-5.6-luna")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    model_client = RetryingSourceRoutingClient()
    planner = CourseSourceRoutingPlanner(
        provider_registry=ProviderRegistry.from_env(),
        model_client=model_client,
    )
    files = [
        _indexed("Lecture01.pdf", "pdf", "a"),
        _indexed("code/regression-demo.ipynb", "notebook", "b"),
    ]
    lecture = Lecture(
        id="lecture-01",
        course_id="course",
        title="Regression",
        date=date(2026, 5, 5),
        material_path="Lecture01.pdf",
    )

    routes = await planner.propose_routes(
        course_id="course",
        files=files,
        lectures=[lecture],
        roots=[],
    )

    assert model_client.selection_calls == 2
    assert model_client.review_calls == 1
    assert "supplemental teaching material" in model_client.selection_messages[-1][-1]["content"]
    assert "selection for every listed path" in model_client.selection_messages[-1][-1]["content"]
    assert routes[1].role == SourceRouteRole.LECTURE
    assert routes[1].lecture_id == "lecture-01"


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


def _indexed(path: str, kind: str, digest: str) -> IndexedSourceFile:
    return IndexedSourceFile(
        path=path,
        kind=kind,
        size_bytes=1,
        sha256=digest * 64,
        modified_ns=1,
    )


class RetryingSourceRoutingClient:
    def __init__(self) -> None:
        self.selection_calls = 0
        self.selection_messages: list[list[dict[str, str]]] = []
        self.review_calls = 0

    async def complete_routing(self, *, messages, **_kwargs):
        self.selection_calls += 1
        self.selection_messages.append(messages)
        if self.selection_calls == 1:
            return {"selections": []}
        return {
            "selections": [
                {
                    "path": "code/regression-demo.ipynb",
                    "role": "lecture",
                    "lecture_id": "lecture-01",
                }
            ]
        }

    async def review_routing(self, **_kwargs):
        self.review_calls += 1
        return {"corrections": []}
