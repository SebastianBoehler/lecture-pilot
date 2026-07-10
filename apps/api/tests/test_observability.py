from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    CanvasCommand,
    QualityGateDecision,
    QualityGateStatus,
    UserMemoryContext,
)
from lecturepilot.observability import Observability, observability_from_env
from lecturepilot.providers import DEFAULT_MODEL
from auth_helpers import student_headers


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
            observability.result_output(
                AgentTurnResult(message="Answer", model=DEFAULT_MODEL)
            )
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


def test_agent_turn_records_workflow_spans(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_OBSERVABILITY", "none")
    app = create_app()
    recording = _RecordingObservability()
    layout = object()
    app.state.observability = recording
    app.state.canvas_workspace = _CanvasWorkspace(layout)
    app.state.user_memory_store = _UserMemoryStore(layout)
    app.state.learner_state = _LearnerState(layout)
    app.state.agent_harness = _GeneratedSectionHarness()
    client = TestClient(app)

    response = client.post(
        "/agent/turn",
        headers=student_headers("u1"),
        json={
            "course_id": "martius-ml",
            "lecture_id": "lecture-03",
            "attendance": "absent",
            "message": "Create a loss section.",
        },
    )

    assert response.status_code == 200
    assert recording.names == [
        "agent_turn",
        "read_canvas",
        "read_user_memory",
        "write_attendance",
        "call_tutor_model",
        "prepare_canvas_update",
        "write_canvas_update",
        "record_quality_gate",
    ]
    assert any(output["quality_gate"] == "needs_evidence" for output in recording.outputs)


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


class _RecordingSpan:
    def __init__(self, observability: "_RecordingObservability", name: str) -> None:
        self.observability = observability
        self.name = name

    def __enter__(self) -> "_RecordingSpan":
        self.observability.names.append(self.name)
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def set_outputs(self, value: dict[str, Any]) -> None:
        self.observability.outputs.append(value)


class _RecordingObservability(Observability):
    def __init__(self) -> None:
        self.names: list[str] = []
        self.outputs: list[dict[str, Any]] = []

    def agent_turn_span(self, turn: AgentTurnInput) -> _RecordingSpan:
        return _RecordingSpan(self, "agent_turn")

    def tool_span(self, name: str, **attributes: Any) -> _RecordingSpan:
        return _RecordingSpan(self, name)

    def model_span(self, **attributes: Any) -> _RecordingSpan:
        return _RecordingSpan(self, "call_tutor_model")


class _CanvasWorkspace:
    def __init__(self, layout: object) -> None:
        self.layout = layout
        self.applied: list[CanvasSection] = []

    def read_document(self, **kwargs: Any) -> CanvasDocument:
        return CanvasDocument(
            id="lecture-03-canvas",
            course_id="martius-ml",
            lecture_id="lecture-03",
            title="Bayesian Decision Theory",
            source_kind="generated",
            source_ref="test",
            workspace_path="canvas/index.md",
        )

    def prepare_generated_sections(self, **kwargs: Any) -> list[CanvasSection]:
        return kwargs["sections"]

    def apply_sections(self, **kwargs: Any) -> None:
        self.applied.extend(kwargs["sections"])


class _UserMemoryStore:
    def __init__(self, layout: object) -> None:
        self.layout = layout

    def read_context(self, user_id: str, course_id: str | None = None) -> UserMemoryContext:
        return UserMemoryContext(
            global_notes="Prefers concrete examples.",
            course_notes="Needs Bayes risk practice." if course_id else "",
        )


class _LearnerState:
    def __init__(self, layout: object) -> None:
        self.layout = layout

    def write_attendance(self, **kwargs: Any) -> None:
        return None

    def record_quality_gate(self, **kwargs: Any) -> None:
        return None


class _GeneratedSectionHarness:
    async def run_turn(self, turn: AgentTurnInput) -> AgentTurnResult:
        section = CanvasSection(id="generated-loss-note", title="Generated Loss Note")
        return AgentTurnResult(
            message="I added a generated section and kept the gate open.",
            canvas_commands=[
                CanvasCommand(type="append_section", section_id=section.id, section=section)
            ],
            quality_gate=QualityGateDecision(
                gate_id="loss-risk-check",
                status=QualityGateStatus.NEEDS_EVIDENCE,
                reason="Needs a worked explanation.",
            ),
            model=DEFAULT_MODEL,
        )
