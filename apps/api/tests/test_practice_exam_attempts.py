from pathlib import Path
from uuid import uuid4

import pytest

from auth_helpers import professor_headers, student_headers
from lecturepilot.assessment_history import load_assessment_history
from lecturepilot.practice_exam_attempts import PracticeAttemptStore, PracticeSubmission
from lecturepilot.practice_exam_store import PracticeExamStore
from lecturepilot.storage_layout import StorageLayout
from test_practice_exam_store import _exam
from test_practice_exam_api import _client, _generate


def test_private_immutable_answers_survive_restart_and_delete_with_exam(tmp_path: Path):
    exams = PracticeExamStore(StorageLayout(tmp_path))
    exam = _exam()
    exams.write(user_id="a", course_id="ml", exam=exam)
    attempts = PracticeAttemptStore(exams)
    submission = PracticeSubmission(
        id=uuid4(),
        answers={"question-01": {"selected_index": 1}, "question-02": {"text": "My reasoning"}},
    )
    args = dict(user_id="a", course_id="ml", exam_id=exam.id)
    saved = attempts.save(**args, submission=submission)
    assert attempts.save(**args, submission=submission) == saved
    assert PracticeAttemptStore(exams).list(**args) == [saved]
    assert saved.assessment == "ungraded"
    assert saved.assistance == "unknown"
    assert "reference_answer" not in saved.model_dump_json()
    with pytest.raises(FileNotFoundError):
        attempts.list(**{**args, "user_id": "b"})
    with pytest.raises(ValueError, match="different answers"):
        attempts.save(**args, submission=PracticeSubmission(id=submission.id, answers={}))
    with pytest.raises(ValueError, match="Invalid multiple-choice"):
        attempts.save(
            **args,
            submission=PracticeSubmission(
                id=uuid4(), answers={"question-01": {"selected_index": 99}}
            ),
        )
    with pytest.raises(ValueError, match="active questions"):
        attempts.save(**args, submission=PracticeSubmission(id=uuid4(), answers={"unknown": {}}))
    exams.delete(**args)
    assert not exams.layout.practice_exam_dir("a", "ml", exam.id).exists()
    with pytest.raises(FileNotFoundError):
        attempts.save(**args, submission=submission)
    assert not exams.layout.practice_exam_dir("a", "ml", exam.id).exists()


def test_attempt_api_auth_retry_validation_and_delete(tmp_path: Path):
    client, _ = _client(tmp_path)
    exam = _generate(client).json()
    route = f"/courses/martius-ml/practice-exams/{exam['id']}/attempts"
    headers = student_headers("student-a")
    payload = {"id": str(uuid4()), "answers": {"q-01": {"selected_index": 1}}}
    first = client.post(route, headers=headers, json=payload)
    assert first.status_code == 200, first.text
    assert client.post(route, headers=headers, json=payload).json() == first.json()
    assert client.get(route, headers=headers).json() == [first.json()]
    assert client.get(route, headers=student_headers("student-b")).status_code == 404
    assert client.get(route, headers=professor_headers()).status_code == 403
    assert client.get(route).status_code == 401
    assert (
        client.post(route, headers=headers, json={**payload, "assessment": "passed"}).status_code
        == 422
    )
    assert (
        client.post(route, headers=headers, json={**payload, "id": "../unsafe"}).status_code == 422
    )
    deleted = client.delete(f"{route}/{payload['id']}", headers=headers)
    assert deleted.status_code == 200
    assert client.get(route, headers=headers).json() == []


def test_tutor_receives_only_private_current_lecture_answers_without_keys(tmp_path: Path):
    exams = PracticeExamStore(StorageLayout(tmp_path))
    exam = _exam()
    exams.write(user_id="a", course_id="ml", exam=exam)
    store = PracticeAttemptStore(exams)
    args = dict(user_id="a", course_id="ml", exam_id=exam.id)
    record = store.save(
        **args,
        submission=PracticeSubmission(
            id=uuid4(),
            answers={
                "question-01": {"selected_index": 0},
                "question-02": {"text": "private reasoning"},
            },
        ),
    )

    def context(user="a", lecture="lecture-02"):
        return load_assessment_history(
            exams.layout, user_id=user, course_id="ml", lecture_id=lecture
        )

    observations = context().observations
    assert len(observations) == 1
    assert observations[0].answer == "private reasoning"
    assert observations[0].assessment == "ungraded"
    assert "invariance" not in context().model_dump_json()
    assert context("b").observations == []
    assert context(lecture="lecture-03").observations == []
    store.delete(**args, attempt_id=record.id)
    assert context().observations == []


def test_existing_readiness_results_are_loaded_with_provenance_not_rubrics(tmp_path: Path):
    from lecturepilot.durable_files import atomic_write_json
    from lecturepilot.models import AgentTurnRequest

    layout = StorageLayout(tmp_path)
    event = dict(
        attempt_id="past",
        question_id="q",
        lecture_id="lecture-01",
        section_id="s",
        answer_kind="open_ended",
        correct=False,
        score=0.25,
        feedback="Explain the distinction.",
        first_try=True,
        attempt_index=1,
        status="needs_revision",
        created_at="2026-09-01T12:00:00Z",
    )
    atomic_write_json(
        layout.user_course_root("a", "ml") / "progress.json",
        {
            "attempts": [event],
            "active_tasks": [],
        },
    )
    context = load_assessment_history(layout, user_id="a", course_id="ml", lecture_id="lecture-01")
    assert context.observations[0].assessment == "ai_assessment"
    assert context.observations[0].score == 0.25
    assert context.observations[0].answer is None
    assert (
        load_assessment_history(
            layout, user_id="a", course_id="other", lecture_id="lecture-01"
        ).observations
        == []
    )
    with pytest.raises(ValueError, match="Extra inputs"):
        AgentTurnRequest.model_validate(
            dict(
                course_id="ml",
                lecture_id="lecture-01",
                attendance="present",
                message="help",
                assessment_history=context.model_dump(),
            )
        )


def test_tutor_prompt_carries_historical_observations_without_gate_authority(tmp_path: Path):
    from lecturepilot.assessment_history_models import (
        AssessmentHistoryContext,
        AssessmentObservation,
    )
    from lecturepilot.model_client import _messages
    from lecturepilot.models import AgentTurnInput

    observation = AssessmentObservation(
        kind="readiness",
        attempt_id="old",
        question_id="q",
        created_at="2026-09-01",
        assessment="ai_assessment",
        correct=False,
        feedback="Explain the difference.",
    )
    turn = AgentTurnInput(
        user_id="a",
        course_id="ml",
        lecture_id="lecture-01",
        attendance="present",
        message="Help me revise.",
        assessment_history=AssessmentHistoryContext(observations=[observation]),
    )
    content = _messages(turn)[-1]["content"]
    assert "Explain the difference." in content
    assert '"assessment":"ai_assessment"' in content
    assert "Do not infer independent mastery" in content
    assert "unknown" in content
