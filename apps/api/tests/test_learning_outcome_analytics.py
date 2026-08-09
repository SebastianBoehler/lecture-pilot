import json
from pathlib import Path

from auth_helpers import professor_headers, student_headers
from canvas_workspace_fixtures import publish_course_canvas
from lecturepilot.agent_gate_persistence import persist_quality_gate
from lecturepilot.coaching_orchestration import prepare_coaching_turn
from lecturepilot.coaching_progress import CoachingTurnEvent
from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    AttendanceStatus,
    QualityGateDecision,
    QualityGateStatus,
)
from lecturepilot.observability import Observability
from test_analytics_routes import _canvas_document, _client


def test_quiz_outcomes_use_one_first_attempt_per_learner_and_keep_versions_separate(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    for index in range(5):
        _answer(client, f"historical-{index}", 1, 0)
    publish_course_canvas(
        client.app.state.canvas_workspace,
        _canvas_document(tmp_path).model_copy(update={"title": "Risk lecture version two"}),
    )
    for attempt_index in range(1, 11):
        _answer(client, "student-a", attempt_index, 1 if attempt_index == 10 else 0)
    for suffix in "bcde":
        _answer(client, f"student-{suffix}", 1, 1)

    response = client.get(
        "/admin/courses/demo-course/lectures/lecture-01/analytics",
        headers=professor_headers(),
    )
    assert response.status_code == 200
    summary = response.json()
    assert [
        (item["publication_version"], item["version_status"]) for item in summary["quizzes"]
    ] == [
        (2, "current"),
        (1, "historical"),
    ]
    assert summary["activity_events"] == 19
    current = summary["quizzes"][0]
    assert current["activity_events"] == 14
    assert current["first_attempt"] == {
        "evidence_type": "quiz_first_attempt",
        "sample_size": 5,
        "data_status": "available",
        "rate": 0.8,
    }
    assert current["correction_after_feedback"] == {
        "evidence_type": "correction_after_feedback",
        "sample_size": 1,
        "data_status": "insufficient_data",
        "rate": None,
    }
    assert current["options"] is None


def test_gate_outcomes_use_attempt_kind_and_suppress_small_cell_categories(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    prepared_by_user = {}
    for index in range(5):
        user_id = f"student-{index}"
        prepared = _prepare_gate(client, user_id)
        prepared_by_user[user_id] = prepared
        _persist_gate(client, prepared, "independent", 1, index < 3)
        _persist_gate(client, prepared, "supported_retry", 2, index < 4)
        _persist_gate(client, prepared, "delayed_transfer", 3, index < 4)
    for attempt_index in range(4, 14):
        _persist_gate(client, prepared_by_user["student-0"], "supported_retry", attempt_index, True)

    response = client.get(
        "/admin/courses/demo-course/lectures/lecture-01/analytics",
        headers=professor_headers(),
    )
    assert response.status_code == 200
    gate = response.json()["gates"][0]
    assert gate["independent_first_pass"]["rate"] == 0.6
    assert gate["supported_retry"]["rate"] == 0.8
    assert gate["delayed_transfer"] == {
        "evidence_type": "delayed_transfer",
        "sample_size": 5,
        "data_status": "available",
        "rate": 0.8,
    }
    serialized = json.dumps(gate)
    for private_field in (
        "attendance_split",
        "status_counts",
        "assistance_level_counts",
        "evidence_counts",
        "reason",
        "created_at",
    ):
        assert private_field not in serialized


def test_course_rollup_weights_current_first_attempts_by_learner(tmp_path: Path) -> None:
    client = _client(tmp_path)
    for attempt_index in range(1, 11):
        _answer(client, "student-a", attempt_index, 1 if attempt_index == 10 else 0)
    for suffix in "bcde":
        _answer(client, f"student-{suffix}", 1, 1)

    response = client.get("/admin/courses/demo-course/analytics", headers=professor_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["activity_events"] == 14
    assert payload["quiz_first_attempt"] == {
        "evidence_type": "quiz_first_attempt",
        "sample_size": 5,
        "data_status": "available",
        "rate": 0.8,
    }
    assert "quiz_attempts" not in payload
    assert "gate_checks" not in payload


def _answer(client, user_id: str, attempt_index: int, option_index: int) -> None:
    response = client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=student_headers(user_id),
        json={
            "attendance": "present",
            "attempt_id": f"{user_id}-attempt-{attempt_index}",
            "block_id": "risk-check",
            "option_index": option_index,
        },
    )
    assert response.status_code == 200


def _prepare_gate(client, user_id: str) -> AgentTurnInput:
    app = client.app
    prepared = prepare_coaching_turn(
        app,
        AgentTurnInput(
            user_id=user_id,
            course_id="demo-course",
            lecture_id="lecture-01",
            attendance=AttendanceStatus.PRESENT,
            message="Assess the published risk gate.",
            canvas_state={"focused_section_id": "risk"},
        ),
        lambda _message: None,
        Observability(),
    )
    assert prepared.active_gate is not None
    return prepared


def _persist_gate(
    client,
    prepared: AgentTurnInput,
    attempt_kind: str,
    attempt_index: int,
    passed: bool,
) -> None:
    app = client.app
    assert prepared.active_gate is not None
    status = QualityGateStatus.PASSED if passed else QualityGateStatus.NEEDS_EVIDENCE
    decision = QualityGateDecision(
        gate_id=prepared.active_gate.id,
        gate_revision=prepared.active_gate.revision,
        status=status,
        reason="Private assessment reason.",
    )
    event = CoachingTurnEvent(
        created_at="2026-08-09T12:00:00+00:00",
        gate_id=prepared.active_gate.id,
        gate_revision=prepared.active_gate.revision,
        gate_status=status,
        support_profile="retrieval",
        process_label="check",
        attempt_kind=attempt_kind,
        attempt_index=attempt_index,
    )
    persist_quality_gate(
        app,
        turn=prepared,
        result=AgentTurnResult(
            message="Assessment complete.", model="contract", quality_gate=decision
        ),
        activity=lambda _message: None,
        observability=Observability(),
        coaching_event=event,
    )
