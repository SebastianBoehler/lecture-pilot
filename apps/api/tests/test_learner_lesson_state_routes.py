from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from canvas_workspace_fixtures import published_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.coaching_state_models import CoachingProgress, DelayedReview, PendingCheck
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.durable_files import atomic_write_json
from lecturepilot.learner_state import LearnerStateStore
from lecturepilot.lecture_access_models import LectureAccessRule
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture, QualityGateDecision
from lecturepilot.professor_preview import professor_preview_user_id
from lecturepilot.quality_gate_models import QualityGateStatus


COURSE_ID = "learner-state-course"
PAST = date(2020, 1, 1)
FUTURE = date(2099, 1, 1)
PREVIEW = {"X-LecturePilot-Learner-Preview": "professor"}


def test_new_learner_receives_explicit_empty_lesson_state(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = _get_state(client, "student-a")

    assert response.status_code == 200
    assert response.json() == {
        "course_id": COURSE_ID,
        "lecture_id": "lecture-open",
        "gate_statuses": {},
        "quiz_states": {},
        "active_session_goal": None,
        "pending_check": None,
        "due_gate_reviews": [],
    }


def test_lesson_state_isolated_to_authenticated_learner_identity(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _record_gate(client, "student-a", "risk-check", QualityGateStatus.PASSED)

    own = _get_state(client, "student-a")
    other = client.get(
        f"{_state_url()}?user_id=student-a",
        headers=student_headers("student-b", course_ids=[COURSE_ID]),
    )

    assert own.json()["gate_statuses"] == {"risk-check": "passed"}
    assert other.json()["gate_statuses"] == {}


def test_lesson_state_enforces_enrollment_unlock_and_publication(tmp_path: Path) -> None:
    client = _client(tmp_path)
    enrolled = student_headers("student-a", course_ids=[COURSE_ID])

    unenrolled = client.get(_state_url(), headers=student_headers("outsider", course_ids=[]))
    locked = client.get(_state_url("lecture-locked"), headers=enrolled)
    hidden = client.get(_state_url("lecture-hidden"), headers=enrolled)
    unpublished = client.get(_state_url("lecture-unpublished"), headers=enrolled)
    unauthenticated = client.get(_state_url())

    assert unenrolled.status_code == 404
    assert locked.status_code == 403
    assert hidden.status_code == 404
    assert unpublished.status_code == 404
    assert unauthenticated.status_code == 401


def test_lesson_state_hydrates_gate_quiz_goal_pending_check_and_due_review(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    user_id = "student-a"
    _record_gate(client, user_id, "risk-check", QualityGateStatus.NEEDS_EVIDENCE)
    quiz = client.post(
        f"/courses/{COURSE_ID}/lectures/lecture-open/analytics/quiz-answer",
        headers=student_headers(user_id, course_ids=[COURSE_ID]),
        json={"attendance": "present", "block_id": "intro-quiz", "option_index": 0},
    )
    now = datetime.now(UTC)
    progress = CoachingProgress(
        session_goal="Compare posterior risk on an unfamiliar case.",
        pending_check=PendingCheck(
            gate_id="risk-check",
            gate_revision="rev-1",
            prompt="Apply the rule to a changed example.",
            assistance_level="prompt",
            issued_at=now.isoformat(),
        ),
        delayed_reviews={
            "risk-check": DelayedReview(
                gate_id="risk-check",
                gate_revision="rev-1",
                scheduled_at=(now - timedelta(days=3)).isoformat(),
                due_at=(now - timedelta(days=1)).isoformat(),
            ),
            "future-check": DelayedReview(
                gate_id="future-check",
                due_at=(now + timedelta(days=1)).isoformat(),
            ),
        },
        messages=[],
    )
    _write_progress(client, user_id, progress)

    state = _get_state(client, user_id)

    assert quiz.status_code == 200
    assert state.status_code == 200
    assert state.json() == {
        "course_id": COURSE_ID,
        "lecture_id": "lecture-open",
        "gate_statuses": {"risk-check": "needs_evidence"},
        "quiz_states": {
            "intro-quiz": {"selected_index": 0, "correct": True},
        },
        "active_session_goal": "Compare posterior risk on an unfamiliar case.",
        "pending_check": {
            "gate_id": "risk-check",
            "gate_revision": "rev-1",
            "prompt": "Apply the rule to a changed example.",
            "assistance_level": "prompt",
            "kind": "standard",
        },
        "due_gate_reviews": [
            {
                "gate_id": "risk-check",
                "gate_revision": "rev-1",
                "due_at": progress.delayed_reviews["risk-check"].due_at,
            }
        ],
    }


def test_professor_preview_read_is_isolated_and_non_mutating(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _record_gate(client, "student-a", "risk-check", QualityGateStatus.PASSED)
    preview_user = professor_preview_user_id("prof-a", COURSE_ID)
    preview_root = client.app.state.canvas_workspace.layout.user_root(preview_user)

    denied = client.get(_state_url(), headers=professor_headers("prof-a"))
    preview = client.get(
        _state_url(),
        headers={**professor_headers("prof-a"), **PREVIEW},
    )

    assert denied.status_code == 403
    assert preview.status_code == 200
    assert preview.json()["gate_statuses"] == {}
    assert not preview_root.exists()
    assert _get_state(client, "student-a").json()["gate_statuses"] == {"risk-check": "passed"}


def test_progress_reset_clears_private_quiz_state(tmp_path: Path) -> None:
    client = _client(tmp_path)
    headers = student_headers("student-a", course_ids=[COURSE_ID])
    quiz_url = f"/courses/{COURSE_ID}/lectures/lecture-open/analytics/quiz-answer"
    assert (
        client.post(
            quiz_url,
            headers=headers,
            json={"attendance": "present", "block_id": "intro-quiz", "option_index": 0},
        ).status_code
        == 200
    )

    reset = client.post(
        f"/courses/{COURSE_ID}/learner-workspace/reset",
        headers=headers,
        json={"reset_canvas": False, "reset_course_memory": False, "reset_progress": True},
    )

    assert reset.status_code == 200
    assert _get_state(client, "student-a").json()["quiz_states"] == {}


def test_professor_analytics_never_exposes_private_tutor_messages(tmp_path: Path) -> None:
    client = _client(tmp_path)
    progress = CoachingProgress(
        session_goal="Private goal",
        messages=[
            {"role": "user", "content": "private learner message"},
            {"role": "assistant", "content": "private tutor message"},
        ],
    )
    _write_progress(client, "student-a", progress)

    response = client.get(
        f"/admin/courses/{COURSE_ID}/lectures/lecture-open/analytics",
        headers=professor_headers("prof-a"),
    )
    serialized = response.text

    assert response.status_code == 200
    assert "private learner message" not in serialized
    assert "private tutor message" not in serialized
    assert '"messages"' not in serialized


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    lectures = [
        Lecture(id="lecture-open", course_id=COURSE_ID, title="Open", date=PAST),
        Lecture(id="lecture-locked", course_id=COURSE_ID, title="Locked", date=FUTURE),
        Lecture(
            id="lecture-hidden",
            course_id=COURSE_ID,
            title="Hidden",
            date=PAST,
            access_override=LectureAccessRule(publication_mode="hidden"),
        ),
        Lecture(id="lecture-unpublished", course_id=COURSE_ID, title="Draft", date=PAST),
    ]
    write_course_workspace(
        app.state.canvas_workspace.course_media_root(COURSE_ID),
        CourseWorkspaceResult(
            course=Course(id=COURSE_ID, title="State", professor="Professor", term="2026"),
            lectures=lectures,
            active_lecture_id="lecture-open",
        ),
    )
    for lecture_id in ("lecture-open", "lecture-locked", "lecture-hidden"):
        document = published_course_canvas(COURSE_ID, lecture_id)
        document.sections[0].blocks.extend(
            [
                CanvasBlock(id="risk-check", type="checkpoint", text="Explain risk."),
                CanvasBlock(
                    id="intro-quiz",
                    type="quiz",
                    text="Choose risk.",
                    items=["Expected risk", "Slide count"],
                    answer_index=0,
                ),
            ]
        )
        app.state.canvas_workspace.write_course_canvas(document)
    return TestClient(app)


def _record_gate(
    client: TestClient,
    user_id: str,
    gate_id: str,
    status: QualityGateStatus,
) -> None:
    LearnerStateStore(client.app.state.canvas_workspace.layout).record_quality_gate(
        course_id=COURSE_ID,
        lecture_id="lecture-open",
        user_id=user_id,
        decision=QualityGateDecision(
            gate_id=gate_id,
            status=status,
            reason="Learner-safe feedback.",
        ),
    )


def _write_progress(client: TestClient, user_id: str, progress: CoachingProgress) -> None:
    path = (
        client.app.state.canvas_workspace.layout.user_lecture_root(
            user_id, COURSE_ID, "lecture-open"
        )
        / "tutor-state.json"
    )
    atomic_write_json(path, progress.model_dump(mode="json"))


def _get_state(client: TestClient, user_id: str):
    return client.get(
        _state_url(),
        headers=student_headers(user_id, course_ids=[COURSE_ID]),
    )


def _state_url(lecture_id: str = "lecture-open") -> str:
    return f"/courses/{COURSE_ID}/lectures/{lecture_id}/learner-state"
