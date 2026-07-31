import json
import sys
from datetime import date
from types import SimpleNamespace

import pytest

from lecturepilot.course_source_routing_planner import (
    CourseSourceRoutingPlanner,
    LiteLLMSourceRoutingClient,
)
from lecturepilot.models import Lecture
from lecturepilot.providers import ProviderConfigurationError, ProviderRegistry
from lecturepilot.source_index_models import IndexedSourceFile


async def test_agent_routes_every_file_from_semantic_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    source = tmp_path / "week-alpha.md"
    source.write_text(
        "# Autoregressive language models\n\nTeacher forcing and perplexity.",
        encoding="utf-8",
    )
    client = _FakeRoutingClient()
    planner = CourseSourceRoutingPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=client,
    )

    routes = await planner.propose_routes(
        course_id="nlp",
        files=[_indexed(source)],
        lectures=[_lecture("lecture-02", "Language Models")],
        roots=[tmp_path],
    )

    assert routes[0].path == "week-alpha.md"
    assert routes[0].role == "lecture"
    assert routes[0].lecture_id == "lecture-02"
    evidence = client.last_messages[1]["content"]
    assert "Language Models" in evidence
    assert "Teacher forcing and perplexity" in evidence


async def test_agent_repairs_incomplete_routing_instead_of_guessing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    first = tmp_path / "alpha.md"
    second = tmp_path / "shared.md"
    first.write_text("# Tokens", encoding="utf-8")
    second.write_text("# Course notation", encoding="utf-8")
    client = _RepairingRoutingClient()
    planner = CourseSourceRoutingPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=client,
    )

    routes = await planner.propose_routes(
        course_id="nlp",
        files=[_indexed(first), _indexed(second)],
        lectures=[_lecture("lecture-01", "Text preprocessing")],
        roots=[tmp_path],
    )

    assert [route.path for route in routes] == ["alpha.md", "shared.md"]
    assert client.calls == 2
    assert "Assign every listed path exactly once" in client.last_messages[-1]["content"]


async def test_agent_rejects_unknown_lecture_assignments(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    source = tmp_path / "alpha.md"
    source.write_text("# Tokens", encoding="utf-8")
    planner = CourseSourceRoutingPlanner(
        provider_registry=ProviderRegistry.from_env("gemini/test-model"),
        model_client=_UnknownLectureRoutingClient(),
    )

    with pytest.raises(ProviderConfigurationError, match="known lecture"):
        await planner.propose_routes(
            course_id="nlp",
            files=[_indexed(source)],
            lectures=[_lecture("lecture-01", "Text preprocessing")],
            roots=[tmp_path],
        )


async def test_litellm_routing_client_requests_strict_schema(monkeypatch) -> None:
    calls = []
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        payload = {"routes": []}
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
        )

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))
    payload = await LiteLLMSourceRoutingClient().complete_routing(
        settings=ProviderRegistry.from_env("gemini/test-model").require_ready([]),
        messages=[{"role": "user", "content": "Route files"}],
    )

    assert payload == {"routes": []}
    response_format = calls[0]["response_format"]
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["required"] == ["routes"]


class _FakeRoutingClient:
    def __init__(self) -> None:
        self.last_messages = []

    async def complete_routing(self, *, settings, messages):
        self.last_messages = messages
        return {
            "routes": [{"path": "week-alpha.md", "role": "lecture", "lecture_id": "lecture-02"}]
        }


class _RepairingRoutingClient:
    def __init__(self) -> None:
        self.calls = 0
        self.last_messages = []

    async def complete_routing(self, *, settings, messages):
        self.calls += 1
        self.last_messages = messages
        if self.calls == 1:
            return {"routes": [{"path": "alpha.md", "role": "excluded", "lecture_id": None}]}
        return {
            "routes": [
                {"path": "alpha.md", "role": "lecture", "lecture_id": "lecture-01"},
                {"path": "shared.md", "role": "course_wide", "lecture_id": None},
            ]
        }


class _UnknownLectureRoutingClient:
    async def complete_routing(self, *, settings, messages):
        return {"routes": [{"path": "alpha.md", "role": "lecture", "lecture_id": "lecture-99"}]}


def _indexed(path) -> IndexedSourceFile:
    return IndexedSourceFile(
        path=path.name,
        kind="markdown",
        size_bytes=path.stat().st_size,
        sha256="a" * 64,
        modified_ns=path.stat().st_mtime_ns,
    )


def _lecture(lecture_id: str, title: str) -> Lecture:
    return Lecture(
        id=lecture_id,
        course_id="nlp",
        title=title,
        date=date(2026, 5, 1),
    )
