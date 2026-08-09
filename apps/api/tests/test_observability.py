from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
)
from lecturepilot.observability import observability_from_env
from lecturepilot.providers import DEFAULT_MODEL


def test_observability_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("LECTUREPILOT_OBSERVABILITY", raising=False)

    observability = observability_from_env()

    assert observability.enabled is False
    with observability.tool_span("read_canvas") as span:
        span.set_outputs({"ok": True})


def test_mlflow_observability_redacts_turn_content(monkeypatch) -> None:
    fake_mlflow = _FakeMlflow()
    monkeypatch.setitem(sys.modules, "mlflow", fake_mlflow)
    monkeypatch.setenv("LECTUREPILOT_OBSERVABILITY", "mlflow")
    monkeypatch.setenv("LECTUREPILOT_TRACE_CONTENT", "redacted")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://mlflow.local:5000")
    monkeypatch.setenv("MLFLOW_EXPERIMENT", "lecturepilot-test")
    turn = AgentTurnInput(
        user_id="raw-student-id",
        course_id="martius-ml",
        lecture_id="lecture-03",
        attendance="absent",
        message="Please explain Bayes.",
    )

    observability = observability_from_env()
    with observability.agent_turn_span(turn) as span:
        span.set_outputs(
            observability.result_output(AgentTurnResult(message="Answer", model=DEFAULT_MODEL))
        )

    recorded = fake_mlflow.started[0]
    assert fake_mlflow.tracking_uri == "http://mlflow.local:5000"
    assert fake_mlflow.experiment == "lecturepilot-test"
    assert recorded.name == "lecturepilot.agent_turn"
    assert recorded.span_type == "CHAIN"
    assert recorded.attributes["user_key"] != "raw-student-id"
    assert recorded.span.inputs["message_sha256"]
    assert "Please explain Bayes." not in str(recorded.span.inputs)
    assert recorded.span.outputs["message_sha256"]


class _FakeSpan:
    def __init__(self) -> None:
        self.inputs: dict[str, Any] = {}
        self.outputs: dict[str, Any] = {}

    def set_inputs(self, value: dict[str, Any]) -> None:
        self.inputs = value

    def set_outputs(self, value: dict[str, Any]) -> None:
        self.outputs = value


class _FakeSpanContext:
    def __init__(self, record: Any) -> None:
        self.record = record

    def __enter__(self) -> _FakeSpan:
        return self.record.span

    def __exit__(self, *args: object) -> bool:
        return False


class _FakeMlflow:
    def __init__(self) -> None:
        self.tracking_uri: str | None = None
        self.experiment: str | None = None
        self.started: list[Any] = []

    def set_tracking_uri(self, value: str) -> None:
        self.tracking_uri = value

    def set_experiment(self, value: str) -> None:
        self.experiment = value

    def start_span(self, **kwargs: Any) -> _FakeSpanContext:
        record = SimpleNamespace(span=_FakeSpan(), **kwargs)
        self.started.append(record)
        return _FakeSpanContext(record)
