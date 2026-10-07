from datetime import UTC, datetime, timedelta

import pytest

from lecturepilot.practice_exam_generation_jobs import PracticeExamGenerationStore
from lecturepilot.storage_layout import StorageLayout


def test_renewed_exam_lease_prevents_a_second_paid_attempt(tmp_path):
    store = PracticeExamGenerationStore(StorageLayout(tmp_path), lease_seconds=180)
    ids = dict(user_id="student-a", course_id="course-1", request_key="practice-exam-key-0001")
    job, owns = store.begin(**ids, input_hash="a" * 64)
    assert owns
    path = store._path(**ids)
    store._write(
        path, job.model_copy(update={"updated_at": datetime.now(UTC) - timedelta(seconds=181)})
    )
    store.renew(job, user_id=ids["user_id"], request_key=ids["request_key"])
    replay, owns = store.begin(**ids, input_hash="a" * 64)
    assert not owns
    assert replay.attempt == job.attempt


def test_superseded_exam_attempt_cannot_renew(tmp_path):
    store = PracticeExamGenerationStore(StorageLayout(tmp_path), lease_seconds=0)
    ids = dict(user_id="student-a", course_id="course-1", request_key="practice-exam-key-0001")
    job, _ = store.begin(**ids, input_hash="a" * 64)
    store.begin(**ids, input_hash="a" * 64)
    with pytest.raises(RuntimeError, match="no longer active"):
        store.renew(job, user_id=ids["user_id"], request_key=ids["request_key"])
