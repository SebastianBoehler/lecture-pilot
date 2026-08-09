from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from canvas_workspace_fixtures import publish_course_canvas
from lecturepilot.analytics_events import InvalidAnalyticsEventError, parse_analytics_event
from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.coaching_progress import CoachingTurnEvent
from lecturepilot.models import AttendanceStatus, QualityGateDecision, QualityGateStatus
from test_analytics_routes import _canvas_document, _client


def test_lecture_headlines_reduce_assessments_within_each_learner_first(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    document = _canvas_document(tmp_path)
    section = document.sections[0]
    quizzes = [_quiz(f"quiz-{index}") for index in range(1, 11)]
    publish_course_canvas(
        client.app.state.canvas_workspace,
        document.model_copy(update={"sections": [section.model_copy(update={"blocks": quizzes})]}),
    )

    for learner in ("student-a", "student-b", "student-c", "student-d", "student-e"):
        _answer(client, learner, "quiz-1", 1 if learner == "student-a" else 0)
    for index in range(2, 11):
        _answer(client, "student-a", f"quiz-{index}", 0)

    lecture = client.get(
        "/admin/courses/demo-course/lectures/lecture-01/analytics",
        headers=professor_headers(),
    )
    course = client.get("/admin/courses/demo-course/analytics", headers=professor_headers())

    assert lecture.status_code == 200
    assert course.status_code == 200
    expected = {
        "evidence_type": "quiz_first_attempt",
        "sample_size": 5,
        "data_status": "available",
        "rate": 0.02,
    }
    assert lecture.json()["quiz_first_attempt"] == expected
    assert course.json()["quiz_first_attempt"] == expected


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
        candidate = {**event, field: invalid}
        with pytest.raises(InvalidAnalyticsEventError):
            parse_analytics_event(json.dumps(candidate))
    with pytest.raises(InvalidAnalyticsEventError):
        parse_analytics_event(json.dumps({**event, "unexpected": True}))

    summary = store.summary(
        course_id="demo-course",
        lecture_id="lecture-01",
        current_publication_version=event["publication_version"],
        current_gate_revisions={},
        current_learning_map_revision="f" * 64,
    )
    assert summary.quizzes[0].version_status == "historical"
    assert summary.quiz_first_attempt.sample_size == 0

    later_version = store.summary(
        course_id="demo-course",
        lecture_id="lecture-01",
        current_publication_version=event["publication_version"] + 1,
        current_gate_revisions={},
        current_learning_map_revision=event["learning_map_revision"],
    )
    assert later_version.quizzes[0].version_status == "historical"
    assert later_version.quiz_first_attempt.sample_size == 0


def test_gate_outcome_requires_exact_publication_map_and_gate_revisions(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    canvas_store = client.app.state.canvas_workspace.course_canvas_store
    context = canvas_store.read_analytics_context(course_id="demo-course", lecture_id="lecture-01")
    gate = context.learning_map.gates[0]
    store = client.app.state.analytics_store
    decision = QualityGateDecision(
        gate_id=gate.id,
        gate_revision=gate.revision,
        status=QualityGateStatus.PASSED,
        reason="The learner supplied sufficient private evidence.",
    )
    store.record_quality_gate(
        course_id="demo-course",
        lecture_id="lecture-01",
        user_id="student-a",
        attendance=AttendanceStatus.PRESENT,
        decision=decision,
        publication_version=context.publication_version,
        learning_map_revision=context.learning_map_revision,
        coaching_event=CoachingTurnEvent(
            created_at="2026-08-09T12:00:00+00:00",
            gate_id=gate.id,
            gate_revision=gate.revision,
            gate_status=QualityGateStatus.PASSED,
            support_profile="retrieval",
            process_label="check",
            attempt_kind="independent",
            attempt_index=1,
        ),
    )

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


def test_quiz_outcome_retry_repairs_cross_file_partial_write_without_duplicates(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    store = client.app.state.analytics_store
    outcome_path = store._events_path("demo-course", "lecture-01")
    outcome_path.mkdir(parents=True)
    request = {
        "attendance": "present",
        "attempt_id": "student-a-risk-check-retry",
        "block_id": "risk-check",
        "option_index": 1,
    }

    failing_client = TestClient(client.app, raise_server_exceptions=False)
    failed = failing_client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=student_headers("student-a"),
        json=request,
    )
    assert failed.status_code == 500
    outcome_path.rmdir()

    repaired = client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=student_headers("student-a"),
        json=request,
    )
    replay = client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=student_headers("student-a"),
        json=request,
    )

    assert repaired.status_code == 200
    assert replay.status_code == 200
    assert repaired.json()["attempt_index"] == 1
    assert replay.json()["attempt_index"] == 1
    assert len(store.events(course_id="demo-course", lecture_id="lecture-01")) == 1


def _quiz(block_id: str) -> CanvasBlock:
    return CanvasBlock(
        id=block_id,
        type="component",
        component_id=block_id,
        component_type="single_choice_quiz",
        caption=f"Retrieval check {block_id}",
        text=f"Which option is correct for {block_id}?",
        items=["Incorrect", "Correct"],
        option_ids=["incorrect", "correct"],
        answer_index=1,
    )


def _answer(client: TestClient, learner: str, block_id: str, option_index: int) -> None:
    response = client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=student_headers(learner),
        json={
            "attendance": "present",
            "attempt_id": f"{learner}-{block_id}-attempt-1",
            "block_id": block_id,
            "option_index": option_index,
        },
    )
    assert response.status_code == 200
