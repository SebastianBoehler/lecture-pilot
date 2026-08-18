from datetime import date

import pytest

from lecturepilot.course_source_routing_planner import CourseSourceRoutingPlanner
from lecturepilot.course_source_routing_models import SourceRouteRole
from lecturepilot.models import Lecture
from lecturepilot.providers import ProviderRegistry
from lecturepilot.source_index_models import IndexedSourceFile


@pytest.mark.asyncio
async def test_planner_keeps_relevant_supplemental_material(monkeypatch) -> None:
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

    assert model_client.selection_calls == 1
    assert model_client.review_calls == 1
    assert routes[1].role == SourceRouteRole.LECTURE
    assert routes[1].lecture_id == "lecture-01"


@pytest.mark.asyncio
async def test_planner_may_exclude_irrelevant_supplemental_material(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_MODEL", "openai/gpt-5.6-luna")
    monkeypatch.setenv("LECTUREPILOT_ALLOWED_MODELS", "openai/gpt-5.6-luna")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    model_client = ExcludingSourceRoutingClient()
    planner = CourseSourceRoutingPlanner(
        provider_registry=ProviderRegistry.from_env(),
        model_client=model_client,
    )
    files = [
        _indexed("Lecture01.pdf", "pdf", "a"),
        _indexed("code/unrelated-demo.ipynb", "notebook", "b"),
    ]
    lecture = Lecture(
        id="lecture-01",
        course_id="course",
        title="Regression",
        date=date(2026, 5, 5),
        material_path="Lecture01.pdf",
    )

    routes = await planner.propose_routes(
        course_id="course", files=files, lectures=[lecture], roots=[]
    )

    assert model_client.selection_calls == 1
    assert routes[1].role == SourceRouteRole.EXCLUDED


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


class ExcludingSourceRoutingClient:
    def __init__(self) -> None:
        self.selection_calls = 0

    async def complete_routing(self, **_kwargs):
        self.selection_calls += 1
        return {"selections": []}

    async def review_routing(self, **_kwargs):
        return {"corrections": []}
