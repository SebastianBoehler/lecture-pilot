from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import lecturepilot.learner_lesson_state_routes as lesson_state_routes
from auth_helpers import student_headers
from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.coaching_state_models import CoachingProgress
from lecturepilot.durable_files import atomic_write_json
from lecturepilot.learner_state import LearnerStateStore
from lecturepilot.models import AttendanceStatus, QualityGateDecision
from lecturepilot.quality_gate_models import QualityGateStatus
from test_learner_lesson_state_routes import COURSE_ID, QUIZ_ANSWER, STATE_URL, _client, _gate


LECTURE_ID = "lecture-open"
RECOVERY_URL = f"{STATE_URL}/recover"
TURN_PAYLOAD = {
    "course_id": COURSE_ID,
    "lecture_id": LECTURE_ID,
    "attendance": "present",
    "message": "Continue the approved check.",
}


@pytest.mark.parametrize(
    ("endpoint", "method"),
    [
        (STATE_URL, "get"),
        ("/agent/turn", "post"),
        ("/agent/turn/stream", "post"),
    ],
)
def test_v1_coaching_state_returns_consistent_recovery_conflict(
    tmp_path: Path, endpoint: str, method: str
) -> None:
    base = _client(tmp_path)
    _write_v1_progress(base, "student-a")
    client = TestClient(base.app, raise_server_exceptions=False)
    headers = student_headers("student-a", course_ids=[COURSE_ID])

    response = (
        client.get(endpoint, headers=headers)
        if method == "get"
        else client.post(endpoint, headers=headers, json=TURN_PAYLOAD)
    )

    assert response.status_code == 409
    assert response.json() == {"detail": _recovery_required_detail()}
    assert response.headers["content-type"].startswith("application/json")


def test_authenticated_recovery_resets_only_ambiguous_coaching_and_gate_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path)
    user_id = "student-a"
    headers = student_headers(user_id, course_ids=[COURSE_ID])
    layout = client.app.state.canvas_workspace.layout
    learner_store = LearnerStateStore(layout)
    gate = _gate(client, "risk-check")
    audit_events = []
    monkeypatch.setattr(
        lesson_state_routes,
        "record_audit_event",
        lambda *_args, **kwargs: audit_events.append(kwargs),
        raising=False,
    )
    _write_v1_progress(client, user_id)
    learner_store.write_attendance(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        user_id=user_id,
        attendance=AttendanceStatus.PRESENT,
    )
    learner_store.record_quality_gate(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        user_id=user_id,
        decision=_decision("risk-check", gate.revision),
    )
    learner_store.record_quality_gate(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        user_id=user_id,
        decision=_decision("retired-gate", "f" * 64),
    )
    quiz = client.post(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/analytics/quiz-answer",
        headers=headers,
        json=QUIZ_ANSWER,
    )
    assert quiz.status_code == 200
    preserved = _write_preserved_sentinels(layout, user_id)
    lecture_root = layout.user_lecture_root(user_id, COURSE_ID, LECTURE_ID)
    tutor_path = lecture_root / "tutor-state.json"
    gates_path = lecture_root / "gates.json"
    target_before_auth = (tutor_path.read_bytes(), gates_path.read_bytes())

    unauthenticated = client.post(RECOVERY_URL)

    assert unauthenticated.status_code == 401
    assert (tutor_path.read_bytes(), gates_path.read_bytes()) == target_before_auth

    recovered = client.post(RECOVERY_URL, headers=headers)

    assert recovered.status_code == 200
    assert recovered.json() == {
        "course_id": COURSE_ID,
        "lecture_id": LECTURE_ID,
        "coaching_state_reset": True,
        "cleared_gate_ids": ["risk-check"],
    }
    assert audit_events == [
        {
            "event_type": "learner.coaching_state_recovered",
            "target_type": "lecture",
            "target_id": LECTURE_ID,
            "details": {
                "course_id": COURSE_ID,
                "cleared_gate_ids": ["risk-check"],
            },
        }
    ]
    progress = CoachingProgressStore(layout).read(
        user_id=user_id,
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
    )
    assert progress == CoachingProgress.empty(course_id=COURSE_ID, lecture_id=LECTURE_ID)
    decisions = learner_store.latest_gate_decisions(
        user_id=user_id,
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
    )
    assert set(decisions) == {"retired-gate"}
    assert decisions["retired-gate"].gate_revision == "f" * 64
    for path, content in preserved.items():
        assert path.read_bytes() == content
    hydrated = client.get(STATE_URL, headers=headers)
    assert hydrated.status_code == 200
    assert hydrated.json()["gate_statuses"] == {"retired-gate": "passed"}
    assert hydrated.json()["quiz_states"]["intro-quiz"]["correct"] is True


def test_recovery_rejects_valid_coaching_state_without_clearing_gate_completion(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    user_id = "student-a"
    headers = student_headers(user_id, course_ids=[COURSE_ID])
    learner_store = LearnerStateStore(client.app.state.canvas_workspace.layout)
    gate = _gate(client, "risk-check")
    learner_store.record_quality_gate(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        user_id=user_id,
        decision=_decision("risk-check", gate.revision),
    )

    response = client.post(RECOVERY_URL, headers=headers)

    assert response.status_code == 409
    assert response.json() == {
        "detail": {
            "code": "coaching_state_recovery_not_required",
            "message": "Persisted coaching state is valid; recovery was not applied.",
        }
    }
    assert set(
        learner_store.latest_gate_decisions(
            user_id=user_id,
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
        )
    ) == {"risk-check"}


def _write_v1_progress(client: TestClient, user_id: str) -> None:
    progress = CoachingProgress.empty(course_id=COURSE_ID, lecture_id=LECTURE_ID).model_dump(
        mode="json"
    )
    progress["schema_version"] = 1
    path = (
        client.app.state.canvas_workspace.layout.user_lecture_root(user_id, COURSE_ID, LECTURE_ID)
        / "tutor-state.json"
    )
    atomic_write_json(path, progress)


def _decision(gate_id: str, revision: str) -> QualityGateDecision:
    return QualityGateDecision(
        gate_id=gate_id,
        gate_revision=revision,
        status=QualityGateStatus.PASSED,
        reason="Previously recorded completion.",
        evidence_ids=[gate_id],
        missing_evidence_ids=[],
    )


def _write_preserved_sentinels(layout, user_id: str) -> dict[Path, bytes]:
    paths = {
        layout.user_lecture_root(user_id, COURSE_ID, LECTURE_ID) / "attendance.json",
        layout.user_lecture_root(user_id, COURSE_ID, LECTURE_ID) / "quizzes.json",
        layout.user_canvas_dir(user_id, COURSE_ID, LECTURE_ID) / "student" / "notes.md",
        layout.user_course_root(user_id, COURSE_ID) / "progress.json",
        layout.user_lecture_root(user_id, COURSE_ID, "unrelated-lecture") / "tutor-state.json",
        layout.course_uploads_dir(COURSE_ID) / "source.txt",
    }
    for index, path in enumerate(sorted(paths)):
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"preserve-{index}".encode())
    return {path: path.read_bytes() for path in paths}


def _recovery_required_detail() -> dict[str, str]:
    return {
        "code": "coaching_state_recovery_required",
        "message": (
            "Persisted coaching state cannot be resumed safely. Use the authenticated "
            "recovery endpoint before continuing."
        ),
        "recovery_path": RECOVERY_URL,
    }
