from __future__ import annotations

from datetime import date

from lecturepilot.course_source_routing_models import SourceRouteRole
from lecturepilot.course_source_routing_planner import CourseSourceRoutingPlanner
from lecturepilot.models import Lecture
from lecturepilot.providers import ProviderRegistry
from lecturepilot.source_index_models import IndexedSourceFile


async def test_agent_keeps_project_metadata_out_of_course_evidence(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_MODEL", "openai/gpt-5.6-luna")
    monkeypatch.setenv("LECTUREPILOT_ALLOWED_MODELS", "openai/gpt-5.6-luna")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    model_client = _ProjectMetadataSelectingClient()
    planner = CourseSourceRoutingPlanner(
        provider_registry=ProviderRegistry.from_env(),
        model_client=model_client,
    )
    files = [
        _file("Lecture01.pdf", "pdf", "a"),
        _file("code/pyproject.toml", "code", "b"),
    ]
    lectures = [
        Lecture(
            id="lecture-01",
            course_id="course",
            title="Regression",
            date=date(2026, 5, 5),
            material_path="Lecture01.pdf",
        )
    ]

    routes = await planner.propose_routes(
        course_id="course",
        files=files,
        lectures=lectures,
        roots=[],
    )

    by_path = {route.path: route for route in routes}
    assert by_path["Lecture01.pdf"].role == SourceRouteRole.LECTURE
    assert by_path["code/pyproject.toml"].role == SourceRouteRole.EXCLUDED
    assert by_path["code/pyproject.toml"].lecture_id is None


class _ProjectMetadataSelectingClient:
    async def complete_routing(self, **_kwargs):
        return {
            "selections": [
                {
                    "path": "code/pyproject.toml",
                    "role": "course_wide",
                    "lecture_id": None,
                }
            ]
        }

    async def review_routing(self, **_kwargs):
        return {
            "corrections": [
                {
                    "path": "code/pyproject.toml",
                    "role": "course_wide",
                    "lecture_id": None,
                }
            ]
        }


def _file(path: str, kind: str, digest: str) -> IndexedSourceFile:
    return IndexedSourceFile(
        path=path,
        kind=kind,
        size_bytes=1,
        sha256=digest * 64,
        modified_ns=1,
    )
