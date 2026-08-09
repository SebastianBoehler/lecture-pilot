from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from lecturepilot.analytics_events import InvalidAnalyticsEventError, parse_analytics_event
from lecturepilot.coaching_progress import CoachingTurnEvent
from lecturepilot.durable_files import atomic_write_text
from lecturepilot.models import AttendanceStatus, QualityGateDecision, QualityGateStatus
from test_analytics_review_contract import _answer
from test_analytics_routes import _client


def test_outcome_events_are_strict_and_map_revision_bound(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _answer(client, "student-a", "risk-check", 1)
    store = client.app.state.analytics_store
    event = store.events(course_id="demo-course", lecture_id="lecture-01")[0]

    assert event["event_id"]
    assert event["learning_map_revision"]
    for field, invalid in (
        ("event_id", ""),
        ("course_id", ""),
        ("publication_version", "1"),
        ("learning_map_revision", " "),
        ("attempt_index", 0),
        ("created_at", "2026-08-09T12:00:00"),
    ):
        with pytest.raises(InvalidAnalyticsEventError):
            parse_analytics_event(json.dumps({**event, field: invalid}))
    with pytest.raises(InvalidAnalyticsEventError):
        parse_analytics_event(json.dumps({**event, "unexpected": True}))

    for version, map_revision in (
        (event["publication_version"], "f" * 64),
        (event["publication_version"] + 1, event["learning_map_revision"]),
    ):
        summary = store.summary(
            course_id="demo-course",
            lecture_id="lecture-01",
            current_publication_version=version,
            current_gate_revisions={},
            current_learning_map_revision=map_revision,
        )
        assert summary.quizzes[0].version_status == "historical"
        assert summary.quiz_first_attempt.sample_size == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"correct": True},
        {"correct_index": 7},
        {"option_id": "wrong-option"},
        {"correction_state": "not_needed"},
        {"event_id": "0" * 64},
    ],
)
def test_quiz_outcome_log_rejects_forged_or_inconsistent_events(
    tmp_path: Path,
    changes: dict,
) -> None:
    client = _client(tmp_path)
    _answer(client, "student-a", "risk-check", 0)
    store = client.app.state.analytics_store
    path = store._events_path("demo-course", "lecture-01")
    event = json.loads(path.read_text(encoding="utf-8"))
    corrupted = {**event, **changes}
    if "event_id" not in changes:
        fields = (
            "type",
            "course_id",
            "lecture_id",
            "user_key",
            "component_id",
            "publication_version",
            "learning_map_revision",
            "attempt_index",
        )
        identity = {field: corrupted[field] for field in fields}
        corrupted["event_id"] = hashlib.sha256(
            json.dumps(identity, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
    atomic_write_text(path, json.dumps(corrupted) + "\n")

    with pytest.raises(InvalidAnalyticsEventError):
        store.events(course_id="demo-course", lecture_id="lecture-01")


@pytest.mark.parametrize(
    ("course_id", "lecture_id"),
    [("other-course", "lecture-01"), ("demo-course", "lecture-02")],
)
def test_outcome_log_rejects_event_from_a_different_path(
    tmp_path: Path, course_id: str, lecture_id: str
) -> None:
    client = _client(tmp_path)
    _answer(client, "student-a", "risk-check", 0)
    store = client.app.state.analytics_store
    valid_path = store._events_path("demo-course", "lecture-01")
    wrong_path = store._events_path(course_id, lecture_id)
    atomic_write_text(wrong_path, valid_path.read_text(encoding="utf-8"))

    with pytest.raises(InvalidAnalyticsEventError):
        store.events(course_id=course_id, lecture_id=lecture_id)


def test_gate_outcome_requires_exact_publication_map_and_gate_revisions(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    context, gate, store = _record_gate(client)

    event = store.events(course_id="demo-course", lecture_id="lecture-01")[0]
    assert event["assistance_before_attempt"] == "none"
    assert event["planned_delay_seconds"] is None
    assert event["observed_delay_seconds"] is None

    for publication_version, map_revision, gate_revision in (
        (context.publication_version + 1, context.learning_map_revision, gate.revision),
        (context.publication_version, "f" * 64, gate.revision),
        (context.publication_version, context.learning_map_revision, "different-revision"),
    ):
        summary = store.summary(
            course_id="demo-course",
            lecture_id="lecture-01",
            current_publication_version=publication_version,
            current_gate_revisions={gate.id: gate_revision},
            current_learning_map_revision=map_revision,
        )
        assert summary.gates[0].version_status == "historical"
        assert summary.independent_first_pass.sample_size == 0


def test_gate_outcome_log_rejects_forged_event_identity(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _, _, store = _record_gate(client)
    path = store._events_path("demo-course", "lecture-01")
    event = json.loads(path.read_text(encoding="utf-8"))
    atomic_write_text(path, json.dumps({**event, "event_id": "0" * 64}) + "\n")

    with pytest.raises(InvalidAnalyticsEventError):
        store.events(course_id="demo-course", lecture_id="lecture-01")


def _record_gate(client):
    canvas_store = client.app.state.canvas_workspace.course_canvas_store
    context = canvas_store.read_analytics_context(course_id="demo-course", lecture_id="lecture-01")
    gate = context.learning_map.gates[0]
    store = client.app.state.analytics_store
    store.record_quality_gate(
        course_id="demo-course",
        lecture_id="lecture-01",
        user_id="student-a",
        attendance=AttendanceStatus.PRESENT,
        decision=QualityGateDecision(
            gate_id=gate.id,
            gate_revision=gate.revision,
            status=QualityGateStatus.PASSED,
            reason="The learner supplied sufficient private evidence.",
            evidence_ids=[gate.id],
            missing_evidence_ids=[],
        ),
        publication_version=context.publication_version,
        learning_map_revision=context.learning_map_revision,
        coaching_event=CoachingTurnEvent(
            created_at=datetime(2026, 8, 9, 12, tzinfo=UTC),
            gate_id=gate.id,
            gate_revision=gate.revision,
            gate_status=QualityGateStatus.PASSED,
            support_profile="retrieval",
            process_label="check",
            attempt_kind="independent",
            attempt_index=1,
            assistance_level="none",
            planned_delay_seconds=None,
            observed_delay_seconds=None,
            evidence_ids=[gate.id],
            missing_evidence_ids=[],
        ),
    )
    return context, gate, store
