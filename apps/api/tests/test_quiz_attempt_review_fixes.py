from datetime import date
from pathlib import Path
import json

import pytest
from fastapi.testclient import TestClient

from auth_helpers import student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_learning_design_store import CourseLearningDesignStore
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture


COURSE_ID = "quiz-review"
LECTURE_ID = "lecture-01"
QUIZ_URL = f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/analytics/quiz-answer"


def test_component_quiz_uses_canonical_id_in_result_storage_and_hydration(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = _submit(client, "risk-component", "component-attempt", 1)
    state = _state(client)

    assert response.status_code == 200
    assert response.json()["block_id"] == "risk-component"
    assert response.json()["component_id"] == "risk-component"
    assert set(state) == {"risk-component"}
    assert state["risk-component"]["selected_index"] == 1
    quiz_path = (
        client.app.state.canvas_workspace.layout.user_lecture_root(
            "student-a", COURSE_ID, LECTURE_ID
        )
        / "quizzes.json"
    )
    stored = json.loads(quiz_path.read_text(encoding="utf-8"))
    assert set(stored["attempts"]) == {"risk-component"}
    events = client.app.state.analytics_store.events(course_id=COURSE_ID, lecture_id=LECTURE_ID)
    assert events[0]["block_id"] == "risk-component"


@pytest.mark.parametrize(
    ("answers", "terminal_state", "event_count"),
    [
        ([0, 1, 0], "corrected", 2),
        ([1, 0], "not_needed", 1),
    ],
)
def test_scored_success_is_terminal_for_new_attempt_ids(
    tmp_path: Path,
    answers: list[int],
    terminal_state: str,
    event_count: int,
) -> None:
    client = _client(tmp_path)

    responses = [
        _submit(client, "risk-quiz", f"terminal-attempt-{index}", answer)
        for index, answer in enumerate(answers)
    ]

    assert all(response.status_code == 200 for response in responses)
    assert responses[-1].json()["correct"] is True
    assert responses[-1].json()["correction_state"] == terminal_state
    assert _state(client)["risk-quiz"]["correction_state"] == terminal_state
    events = client.app.state.analytics_store.events(course_id=COURSE_ID, lecture_id=LECTURE_ID)
    assert len(events) == event_count
    if answers == [0, 1, 0]:
        replay = _submit(client, "risk-quiz", "terminal-attempt-0", 0)
        assert replay.json()["correct"] is False
        assert _state(client)["risk-quiz"]["correction_state"] == "corrected"
        assert (
            len(client.app.state.analytics_store.events(course_id=COURSE_ID, lecture_id=LECTURE_ID))
            == 2
        )


def test_unscored_attempt_is_not_misclassified_as_needing_correction(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = _submit(client, "reflection-quiz", "unscored-attempt", 0)

    assert response.status_code == 200
    assert response.json()["latest_outcome"] == "unscored"
    assert response.json()["correction_state"] == "not_needed"


def test_non_quiz_component_is_rejected_even_when_it_has_options_and_a_key(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = _submit(client, "risk-chart", "chart-attempt", 1)

    assert response.status_code == 400
    assert response.json()["detail"] == "Canvas block is not a quiz component."
    assert client.app.state.analytics_store.events(course_id=COURSE_ID, lecture_id=LECTURE_ID) == []


def test_republication_hides_old_state_and_restarts_attempt_index(tmp_path: Path) -> None:
    client = _client(tmp_path)
    first = _submit(client, "risk-quiz", "version-one-attempt", 0)
    assert first.status_code == 200
    assert first.json()["attempt_index"] == 1
    assert first.json()["publication_version"] == 1
    assert "risk-quiz" in _state(client)

    _publish(client, version_two=True)

    assert _state(client) == {}
    current = _submit(client, "risk-quiz", "version-two-attempt", 1)
    assert current.status_code == 200
    assert current.json()["attempt_index"] == 1
    assert current.json()["publication_version"] == 2
    assert _state(client)["risk-quiz"] == {
        "selected_index": 1,
        "correct": True,
        "publication_version": 2,
        "attempt_index": 1,
        "first_attempt_correct": True,
        "latest_outcome": "correct",
        "correction_state": "not_needed",
    }


def _submit(client: TestClient, quiz_id: str, attempt_id: str, option_index: int):
    return client.post(
        QUIZ_URL,
        headers=student_headers("student-a", course_ids=[COURSE_ID]),
        json={
            "attendance": "present",
            "attempt_id": attempt_id,
            "block_id": quiz_id,
            "option_index": option_index,
        },
    )


def _state(client: TestClient) -> dict:
    response = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/learner-state",
        headers=student_headers("student-a", course_ids=[COURSE_ID]),
    )
    assert response.status_code == 200
    return response.json()["quiz_states"]


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    write_course_workspace(
        app.state.canvas_workspace.course_media_root(COURSE_ID),
        CourseWorkspaceResult(
            course=Course(id=COURSE_ID, title="Quiz", professor="Professor", term="2026"),
            lectures=[
                Lecture(id=LECTURE_ID, course_id=COURSE_ID, title="Risk", date=date(2020, 1, 1))
            ],
            active_lecture_id=LECTURE_ID,
        ),
    )
    client = TestClient(app)
    _publish(client)
    return client


def _publish(client: TestClient, *, version_two: bool = False) -> None:
    document = _document(version_two=version_two)
    workspace = client.app.state.canvas_workspace
    manifest = workspace.layout.lecture_source_manifest_path(COURSE_ID, LECTURE_ID)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        '{"course_id":"quiz-review","lecture_id":"lecture-01",'
        '"files":[{"path":"source.md","sha256":"' + "a" * 64 + '"}]}',
        encoding="utf-8",
    )
    workspace.write_course_canvas_draft(document)
    reviews = CourseLearningDesignStore(workspace.layout)
    current = reviews.read(course_id=COURSE_ID, lecture_id=LECTURE_ID)
    reviews.approve(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        draft_digest=current.draft_digest,
        source_revision=current.source_revision,
        learning_map_revision=current.learning_map.revision,
        approved_by="professor",
    )
    workspace.publish_course_canvas_draft(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        published_by="professor",
    )


def _document(*, version_two: bool) -> CanvasDocument:
    return CanvasDocument(
        id=f"{COURSE_ID}-{LECTURE_ID}",
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
                        text="What should be minimized now?"
                        if version_two
                        else "What should be minimized?",
                        items=["Posterior only", "Expected risk"],
                        answer_index=1,
                    ),
                    CanvasBlock(
                        id="risk-component-shell",
                        type="component",
                        component_id="risk-component",
                        component_type="single_choice_quiz",
                        text="Which quantity?",
                        items=["Posterior only", "Expected risk"],
                        answer_index=1,
                    ),
                    CanvasBlock(
                        id="risk-chart",
                        type="component",
                        component_id="risk-chart",
                        component_type="interactive_chart",
                        text="Explore risk.",
                        items=["Posterior only", "Expected risk"],
                        answer_index=1,
                    ),
                    CanvasBlock(
                        id="reflection-quiz",
                        type="quiz",
                        text="Which explanation fits?",
                        items=["Explanation A", "Explanation B"],
                    ),
                ],
            )
        ],
    )
