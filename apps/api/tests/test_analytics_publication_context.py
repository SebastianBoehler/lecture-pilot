from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier, Event

from lecturepilot.agent_gate_persistence import persist_quality_gate
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.coaching_orchestration import prepare_coaching_turn
from lecturepilot.coaching_progress import CoachingTurnEvent
from lecturepilot.learning_map import build_learning_map
from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    AttendanceStatus,
    QualityGateDecision,
    QualityGateStatus,
)
from lecturepilot.observability import Observability
from test_quiz_publication_integrity import _client, _publish


def test_canvas_analytics_context_never_tears_during_real_publication(tmp_path: Path) -> None:
    initial = _gate_document("Version 1")
    client = _client(tmp_path, initial)
    store = client.app.state.canvas_workspace.course_canvas_store
    documents = [_gate_document(f"Version {version}") for version in range(2, 9)]
    expected = {
        1: store.read_analytics_context(
            course_id="quiz-snapshot", lecture_id="lecture-01"
        ).learning_map_revision
    }
    for version, document in enumerate(documents, start=2):
        expected[version] = build_learning_map(document).revision

    start = Barrier(2)
    finished = Event()

    def publish_all() -> None:
        start.wait()
        for document in documents:
            _publish(client, document)
        finished.set()

    observed: list[tuple[int, str | None]] = []
    with ThreadPoolExecutor(max_workers=1) as pool:
        publication = pool.submit(publish_all)
        start.wait()
        while not finished.is_set() or len(observed) < 8:
            context = store.read_analytics_context(
                course_id="quiz-snapshot", lecture_id="lecture-01"
            )
            observed.append((context.publication_version, context.learning_map_revision))
        publication.result(timeout=10)

    assert observed
    assert all(expected[version] == revision for version, revision in observed)
    assert (
        store.read_analytics_context(
            course_id="quiz-snapshot", lecture_id="lecture-01"
        ).publication_version
        == 8
    )


def test_gate_persistence_keeps_context_captured_before_real_republication(tmp_path: Path) -> None:
    client = _client(tmp_path, _gate_document("Version 1"))
    app = client.app
    turn = AgentTurnInput(
        user_id="student-a",
        course_id="quiz-snapshot",
        lecture_id="lecture-01",
        attendance=AttendanceStatus.PRESENT,
        message="Test my understanding.",
        canvas_state={"focused_section_id": "risk"},
    )
    captured = prepare_coaching_turn(app, turn, lambda _message: None, Observability())
    assert captured.active_gate is not None
    assert captured.analytics_context is not None
    assert captured.analytics_context.publication_version == 1

    _publish(client, _gate_document("Version 2"))
    current = app.state.canvas_workspace.course_canvas_store.read_analytics_context(
        course_id="quiz-snapshot", lecture_id="lecture-01"
    )
    assert current.publication_version == 2

    decision = QualityGateDecision(
        gate_id=captured.active_gate.id,
        gate_revision=captured.active_gate.revision,
        status=QualityGateStatus.PASSED,
        reason="This reason must remain private.",
        evidence_ids=[captured.active_gate.id],
        missing_evidence_ids=[],
    )
    coaching_event = CoachingTurnEvent(
        created_at=datetime(2026, 8, 9, 12, tzinfo=UTC),
        gate_id=captured.active_gate.id,
        gate_revision=captured.active_gate.revision,
        gate_status=QualityGateStatus.PASSED,
        support_profile="retrieval",
        process_label="check",
        attempt_kind="independent",
        attempt_index=1,
        assistance_level="none",
        planned_delay_seconds=None,
        observed_delay_seconds=None,
        evidence_ids=[captured.active_gate.id],
        missing_evidence_ids=[],
    )
    persist_quality_gate(
        app,
        turn=captured,
        result=AgentTurnResult(message="Passed.", model="contract-test", quality_gate=decision),
        activity=lambda _message: None,
        observability=Observability(),
        coaching_event=coaching_event,
    )

    [event] = app.state.analytics_store.events(course_id="quiz-snapshot", lecture_id="lecture-01")
    assert event["publication_version"] == 1
    assert event["learning_map_revision"] == captured.analytics_context.learning_map_revision
    assert event["gate_revision"] == captured.active_gate.revision
    assert "reason" not in event


def _gate_document(title: str) -> CanvasDocument:
    return CanvasDocument(
        id="quiz-snapshot-lecture-01",
        course_id="quiz-snapshot",
        lecture_id="lecture-01",
        title=title,
        source_kind="generated",
        source_ref="source.md",
        workspace_path="course/index.md",
        sections=[
            CanvasSection(
                id="risk",
                title="Risk",
                source_ref="source.md",
                blocks=[
                    CanvasBlock(
                        id="risk-gate",
                        type="checkpoint",
                        caption="Risk evidence gate",
                        text="Explain how posterior and loss determine the action.",
                    )
                ],
            )
        ],
    )
