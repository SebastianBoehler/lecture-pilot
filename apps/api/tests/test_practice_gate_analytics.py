import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from lecturepilot.agent_gate_persistence import persist_quality_gate
from lecturepilot.analytics_events import outcome_event_id, parse_analytics_event
from lecturepilot.coaching_analytics import gate_metrics
from lecturepilot.coaching_progress import CoachingTurnEvent
from lecturepilot.learning_map_models import HARDENING_GATE_FIELDS, LearningMapGate, digest_payload
from lecturepilot.models import AgentTurnResult, QualityGateDecision, QualityGateStatus
from lecturepilot.observability import Observability
from test_analytics_routes import _client
from test_learning_outcome_analytics import _prepare_gate


def test_professor_first_pass_uses_independent_exit_not_diagnostic_success() -> None:
    revision = "a" * 64
    metrics = gate_metrics(
        [
            _event("diagnostic", 1, "passed", revision),
            _event("independent_exit", 1, "needs_evidence", revision),
        ],
        current_publication_version=1,
        current_learning_map_revision="map-1",
        current_gate_revisions={"gate-1": revision},
    )

    [gate] = metrics
    assert gate.activity_events == 2
    assert gate.independent_first_pass.sample_size == 1
    assert gate.independent_first_pass.rate is None


def test_legacy_independent_events_remain_compatible() -> None:
    revision = "a" * 64
    payload = {
        **_event("independent", 1, "passed", revision),
        "course_id": "course-1",
        "lecture_id": "lecture-1",
        "attendance": "present",
        "assistance_before_attempt": "none",
        "planned_delay_seconds": None,
        "observed_delay_seconds": None,
        "created_at": "2026-08-26T12:00:00+00:00",
    }
    parsed = parse_analytics_event(json.dumps({**payload, "event_id": outcome_event_id(payload)}))

    [gate] = gate_metrics(
        [parsed.model_dump(mode="json")],
        current_publication_version=1,
        current_learning_map_revision="map-1",
        current_gate_revisions={"gate-1": revision},
    )

    assert gate.independent_first_pass.sample_size == 1


@pytest.mark.parametrize("legacy_gate", [False, True])
def test_only_passed_independent_exit_updates_gate_completion(
    tmp_path: Path, legacy_gate: bool
) -> None:
    client = _client(tmp_path)
    turn = _prepare_gate(client, "student-a")
    assert turn.active_gate is not None
    if legacy_gate:
        payload = turn.active_gate.model_dump(
            mode="json", exclude={"revision", *HARDENING_GATE_FIELDS}
        )
        gate = LearningMapGate.model_validate({**payload, "revision": digest_payload(payload)})
        turn = turn.model_copy(update={"active_gate": gate})
    gate = turn.active_gate
    pass_decision = _decision(gate.id, gate.revision, QualityGateStatus.PASSED)
    fail_decision = _decision(gate.id, gate.revision, QualityGateStatus.NEEDS_EVIDENCE)

    for kind, index, decision in (
        ("diagnostic", 1, pass_decision),
        ("supported_retry", 1, pass_decision),
        ("independent", 1, pass_decision),
        ("independent_exit", 1, fail_decision),
    ):
        _persist(client, turn, decision, kind, index)
        assert (
            client.app.state.learner_state.latest_gate_decisions(
                user_id="student-a",
                course_id="demo-course",
                lecture_id="lecture-01",
            )
            == {}
        )

    _persist(client, turn, pass_decision, "independent_exit", 2)

    stored = client.app.state.learner_state.latest_gate_decisions(
        user_id="student-a",
        course_id="demo-course",
        lecture_id="lecture-01",
    )
    assert stored[gate.id].status == QualityGateStatus.PASSED
    events = client.app.state.analytics_store.events(
        course_id="demo-course", lecture_id="lecture-01"
    )
    assert [event["attempt_kind"] for event in events] == [
        "diagnostic",
        "supported_retry",
        "independent",
        "independent_exit",
        "independent_exit",
    ]
    assert all("reason" not in event and "learner_text" not in event for event in events)


@pytest.mark.parametrize("invalid_field", ["active_gate", "analytics_context"])
def test_gate_persistence_still_rejects_invalid_assessment_context(
    tmp_path: Path, invalid_field: str
) -> None:
    client = _client(tmp_path)
    turn = _prepare_gate(client, "student-a")
    assert turn.active_gate is not None
    gate = turn.active_gate
    invalid_value = (
        gate.model_copy(update={"prompt": "Changed without updating the revision."})
        if invalid_field == "active_gate"
        else None
    )
    turn = turn.model_copy(update={invalid_field: invalid_value})
    decision = _decision(gate.id, gate.revision, QualityGateStatus.NEEDS_EVIDENCE)

    with pytest.raises(ValidationError, match=invalid_field):
        _persist(client, turn, decision, "diagnostic", 1)

    assert (
        client.app.state.analytics_store.events(course_id="demo-course", lecture_id="lecture-01")
        == []
    )


def _persist(client, turn, decision, kind: str, index: int) -> None:
    persist_quality_gate(
        client.app,
        turn=turn,
        result=AgentTurnResult(
            message="Private learner-facing feedback.",
            model="contract",
            quality_gate=decision,
        ),
        activity=lambda _message: None,
        observability=Observability(),
        coaching_event=CoachingTurnEvent(
            created_at=datetime(2026, 8, 26, 12, tzinfo=UTC),
            gate_id=decision.gate_id,
            gate_revision=decision.gate_revision,
            gate_status=decision.status,
            support_profile="self_explanation",
            process_label="self_explanation",
            attempt_kind=kind,
            attempt_index=index,
            assistance_level="none",
            planned_delay_seconds=None,
            observed_delay_seconds=None,
            evidence_ids=decision.evidence_ids,
            missing_evidence_ids=decision.missing_evidence_ids,
        ),
    )


def _decision(gate_id: str, revision: str, status: QualityGateStatus):
    passed = status == QualityGateStatus.PASSED
    return QualityGateDecision(
        gate_id=gate_id,
        gate_revision=revision,
        status=status,
        reason="Private assessment reason.",
        evidence_ids=[gate_id] if passed else [],
        missing_evidence_ids=[] if passed else [gate_id],
    )


def _event(kind: str, index: int, status: str, revision: str) -> dict:
    return {
        "type": "gate_decision",
        "gate_id": "gate-1",
        "gate_revision": revision,
        "publication_version": 1,
        "learning_map_revision": "map-1",
        "user_key": "learner-1",
        "attempt_kind": kind,
        "attempt_index": index,
        "status": status,
    }
