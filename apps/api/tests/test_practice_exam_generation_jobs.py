from __future__ import annotations

from lecturepilot import practice_exam_generation_jobs
from lecturepilot.practice_exam_generation_jobs import PracticeExamGenerationStore
from lecturepilot.storage_layout import StorageLayout


def test_generation_begin_replays_same_active_job(tmp_path) -> None:
    store = PracticeExamGenerationStore(StorageLayout(tmp_path), lease_seconds=30)
    first, owns_first = store.begin(
        user_id="student-a",
        course_id="course-1",
        request_key="practice-exam-key-0001",
        input_hash="a" * 64,
    )
    replay, owns_replay = store.begin(
        user_id="student-a",
        course_id="course-1",
        request_key="practice-exam-key-0001",
        input_hash="a" * 64,
    )

    assert owns_first is True
    assert owns_replay is False
    assert replay.generation_id == first.generation_id


def test_stale_generation_is_reclaimed(tmp_path) -> None:
    store = PracticeExamGenerationStore(StorageLayout(tmp_path), lease_seconds=0)
    first, _ = store.begin(
        user_id="student-a",
        course_id="course-1",
        request_key="practice-exam-key-0001",
        input_hash="a" * 64,
    )

    reclaimed, owns = store.begin(
        user_id="student-a",
        course_id="course-1",
        request_key="practice-exam-key-0001",
        input_hash="a" * 64,
    )

    assert owns is True
    assert reclaimed.generation_id == first.generation_id
    assert reclaimed.attempt == 2


def test_generation_completion_failure_and_input_binding(tmp_path) -> None:
    store = PracticeExamGenerationStore(StorageLayout(tmp_path), lease_seconds=30)
    completed, _ = store.begin(
        user_id="student-a",
        course_id="course-1",
        request_key="practice-exam-key-0001",
        input_hash="a" * 64,
    )
    completed = store.complete(
        completed,
        user_id="student-a",
        request_key="practice-exam-key-0001",
        exam_id="b" * 32,
    )
    assert completed.status == "completed"
    assert completed.exam_id == "b" * 32

    failed, _ = store.begin(
        user_id="student-a",
        course_id="course-1",
        request_key="practice-exam-key-0002",
        input_hash="a" * 64,
    )
    failed = store.fail(
        failed,
        user_id="student-a",
        request_key="practice-exam-key-0002",
        error_code="provider_error",
    )
    assert failed.status == "failed"
    assert failed.error_code == "provider_error"

    try:
        store.begin(
            user_id="student-a",
            course_id="course-1",
            request_key="practice-exam-key-0001",
            input_hash="c" * 64,
        )
    except ValueError as exc:
        assert "different input" in str(exc)
    else:
        raise AssertionError("Expected idempotency input mismatch.")


def test_generation_jobs_are_user_isolated(tmp_path) -> None:
    store = PracticeExamGenerationStore(StorageLayout(tmp_path), lease_seconds=30)
    store.begin(
        user_id="student-a",
        course_id="course-1",
        request_key="practice-exam-key-0001",
        input_hash="a" * 64,
    )

    assert (
        store.read(
            user_id="student-b",
            course_id="course-1",
            request_key="practice-exam-key-0001",
        )
        is None
    )


def test_generation_prunes_old_terminal_records_but_keeps_running(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(practice_exam_generation_jobs, "MAX_TERMINAL_RECORDS", 2)
    store = PracticeExamGenerationStore(StorageLayout(tmp_path), lease_seconds=30)
    store.begin(
        user_id="student-a",
        course_id="course-1",
        request_key="practice-exam-running",
        input_hash="a" * 64,
    )
    for index in range(4):
        key = f"practice-exam-terminal-{index}"
        job, _ = store.begin(
            user_id="student-a",
            course_id="course-1",
            request_key=key,
            input_hash="a" * 64,
        )
        store.fail(job, user_id="student-a", request_key=key, error_code="test")

    directory = store.layout.practice_exam_generations_dir("student-a", "course-1")
    records = [
        practice_exam_generation_jobs.PracticeExamGenerationJob.model_validate_json(
            path.read_text(encoding="utf-8")
        )
        for path in directory.glob("*.json")
    ]
    assert len([item for item in records if item.status == "running"]) == 1
    assert len([item for item in records if item.status == "failed"]) == 2
