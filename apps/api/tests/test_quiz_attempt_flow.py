from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from canvas_workspace_fixtures import configure_canvas_workspace, publish_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture


COURSE_ID = "quiz-flow"
LECTURE_ID = "lecture-01"
QUIZ_URL = f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/analytics/quiz-answer"


def test_learner_canvas_redacts_quiz_key_but_authorized_previews_retain_it(tmp_path: Path) -> None:
    client = _client(tmp_path)

    learner = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas",
        headers=student_headers("student-a", course_ids=[COURSE_ID]),
    )
    preview = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas",
        headers={
            **professor_headers("professor"),
            "X-LecturePilot-Learner-Preview": "professor",
        },
    )
    draft = client.get(
        f"/admin/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas/draft",
        headers=professor_headers("professor"),
    )

    assert learner.status_code == 200
    assert "answer_index" not in learner.text
    assert _quiz(preview.json())["answer_index"] == 1
    assert _quiz(draft.json())["answer_index"] == 1


def test_wrong_then_correct_is_one_first_attempt_plus_one_correction(tmp_path: Path) -> None:
    client = _client(tmp_path)
    headers = student_headers("student-a", course_ids=[COURSE_ID])

    wrong = client.post(
        QUIZ_URL,
        headers=headers,
        json={
            "attendance": "present",
            "attempt_id": "attempt-wrong",
            "block_id": "risk-quiz",
            "option_index": 0,
        },
    )
    duplicate = client.post(
        QUIZ_URL,
        headers=headers,
        json={
            "attendance": "present",
            "attempt_id": "attempt-wrong",
            "block_id": "risk-quiz",
            "option_index": 0,
        },
    )
    corrected = client.post(
        QUIZ_URL,
        headers=headers,
        json={
            "attendance": "present",
            "attempt_id": "attempt-correction",
            "block_id": "risk-quiz",
            "option_index": 1,
        },
    )

    assert wrong.status_code == duplicate.status_code == corrected.status_code == 200
    assert wrong.json() == duplicate.json()
    assert wrong.json() == {
        "block_id": "risk-quiz",
        "component_id": "risk-quiz",
        "selected_index": 0,
        "correct": False,
        "publication_version": 1,
        "attempt_index": 1,
        "first_attempt_correct": False,
        "latest_outcome": "incorrect",
        "correction_state": "needed",
        "feedback": (
            "Review the explanation above, explain why your choice does not fit, "
            "then try a correction."
        ),
    }
    assert corrected.json()["attempt_index"] == 2
    assert corrected.json()["first_attempt_correct"] is False
    assert corrected.json()["latest_outcome"] == "correct"
    assert corrected.json()["correction_state"] == "corrected"
    assert "correct_index" not in corrected.json()

    state = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/learner-state",
        headers=headers,
    ).json()["quiz_states"]["risk-quiz"]
    assert state == {
        "selected_index": 1,
        "correct": True,
        "publication_version": 1,
        "attempt_index": 2,
        "first_attempt_correct": False,
        "latest_outcome": "correct",
        "correction_state": "corrected",
    }
    events = client.app.state.analytics_store.events(course_id=COURSE_ID, lecture_id=LECTURE_ID)
    assert [(event["attempt_index"], event["correct"]) for event in events] == [
        (1, False),
        (2, True),
    ]


def test_concurrent_transport_replay_accepts_one_first_attempt(tmp_path: Path) -> None:
    client = _client(tmp_path)
    headers = student_headers("student-a", course_ids=[COURSE_ID])
    payload = {
        "attendance": "present",
        "attempt_id": "attempt-concurrent-replay",
        "block_id": "risk-quiz",
        "option_index": 0,
    }

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(lambda _: client.post(QUIZ_URL, headers=headers, json=payload), range(2))
        )

    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    events = client.app.state.analytics_store.events(course_id=COURSE_ID, lecture_id=LECTURE_ID)
    assert len(events) == 1
    assert events[0]["attempt_index"] == 1


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    configure_canvas_workspace(
        app,
        CanvasWorkspace(
            workspace_root=tmp_path / "workspaces",
            material_root=tmp_path / "materials",
        ),
    )
    write_course_workspace(
        app.state.canvas_workspace.course_media_root(COURSE_ID),
        CourseWorkspaceResult(
            course=Course(id=COURSE_ID, title="Quiz", professor="Professor", term="2026"),
            lectures=[
                Lecture(
                    id=LECTURE_ID,
                    course_id=COURSE_ID,
                    title="Risk",
                    date=date(2020, 1, 1),
                )
            ],
            active_lecture_id=LECTURE_ID,
        ),
    )
    document = CanvasDocument(
        id="quiz-flow-lecture-01",
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        title="Risk",
        source_kind="generated",
        source_ref="test source",
        workspace_path="course/index.md",
        sections=[
            CanvasSection(
                id="risk",
                title="Risk",
                blocks=[
                    CanvasBlock(
                        id="risk-quiz",
                        type="quiz",
                        text="What should be minimized?",
                        items=["Posterior only", "Expected risk"],
                        answer_index=1,
                    )
                ],
            )
        ],
    )
    publish_course_canvas(app.state.canvas_workspace, document)
    app.state.canvas_workspace.write_course_canvas_draft(document)
    return TestClient(app)


def _quiz(payload: dict) -> dict:
    return payload["sections"][0]["blocks"][0]
