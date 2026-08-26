from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from auth_helpers import student_headers
from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.coaching_state_models import CoachingProgress
from lecturepilot.durable_files import atomic_write_json, exclusive_file_lock
from lecturepilot.learner_state import LearnerStateStore
from test_coaching_state_recovery_routes import (
    COURSE_ID,
    LECTURE_ID,
    RECOVERY_URL,
    _client,
    _decision,
    _gate,
    _write_v1_progress,
)


def test_recovery_serializes_newer_tutor_and_gate_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path)
    user_id = "student-a"
    layout = client.app.state.canvas_workspace.layout
    learner_store = LearnerStateStore(layout)
    gate = _gate(client, "risk-check")
    _write_v1_progress(client, user_id)
    learner_store.record_quality_gate(
        user_id=user_id,
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        decision=_decision(gate.id, gate.revision),
    )
    tutor_path = layout.user_lecture_root(user_id, COURSE_ID, LECTURE_ID) / "tutor-state.json"
    newer = CoachingProgress.empty(course_id=COURSE_ID, lecture_id=LECTURE_ID)
    newer.session_goal = "Keep the newer coaching session."
    reached_validation = Barrier(2)
    release_validation = Barrier(2)
    writer_started = Barrier(2)
    original_read = CoachingProgressStore.read

    def blocked_read(store, **ids):
        try:
            return original_read(store, **ids)
        finally:
            reached_validation.wait(timeout=5)
            release_validation.wait(timeout=5)

    monkeypatch.setattr(CoachingProgressStore, "read", blocked_read)

    def write_newer_state() -> None:
        writer_started.wait(timeout=5)
        with exclusive_file_lock(tutor_path):
            atomic_write_json(tutor_path, newer.model_dump(mode="json"))
        learner_store.record_quality_gate(
            user_id=user_id,
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
            decision=_decision(gate.id, gate.revision).model_copy(
                update={"reason": "Newer completion must survive."}
            ),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        recovery = pool.submit(
            client.post,
            RECOVERY_URL,
            headers=student_headers(user_id, course_ids=[COURSE_ID]),
        )
        reached_validation.wait(timeout=5)
        writer = pool.submit(write_newer_state)
        writer_started.wait(timeout=5)
        release_validation.wait(timeout=5)
        response = recovery.result(timeout=5)
        writer.result(timeout=5)

    assert response.status_code == 200
    assert (
        original_read(
            CoachingProgressStore(layout),
            user_id=user_id,
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
        )
        == newer
    )
    decisions = learner_store.latest_gate_decisions(
        user_id=user_id,
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
    )
    assert decisions[gate.id].reason == "Newer completion must survive."


def test_recovery_rejects_exact_byte_change_before_gate_clear(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _client(tmp_path)
    user_id = "student-a"
    layout = client.app.state.canvas_workspace.layout
    learner_store = LearnerStateStore(layout)
    gate = _gate(client, "risk-check")
    _write_v1_progress(client, user_id)
    learner_store.record_quality_gate(
        user_id=user_id,
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        decision=_decision(gate.id, gate.revision),
    )
    tutor_path = layout.user_lecture_root(user_id, COURSE_ID, LECTURE_ID) / "tutor-state.json"
    newer = CoachingProgress.empty(course_id=COURSE_ID, lecture_id=LECTURE_ID)
    newer.session_goal = "State changed during recovery validation."
    original_read = CoachingProgressStore.read

    def mutate_after_read(store, **ids):
        try:
            return original_read(store, **ids)
        finally:
            atomic_write_json(tutor_path, newer.model_dump(mode="json"))

    monkeypatch.setattr(CoachingProgressStore, "read", mutate_after_read)

    response = client.post(
        RECOVERY_URL,
        headers=student_headers(user_id, course_ids=[COURSE_ID]),
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "coaching_state_recovery_not_required"
    assert CoachingProgress.model_validate_json(tutor_path.read_text()) == newer
    assert set(
        learner_store.latest_gate_decisions(
            user_id=user_id,
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
        )
    ) == {gate.id}
