from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.latex_canvas_importer import CANVAS_IMPORT_VERSION
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture


COURSE_ID = "overlay-quiz"
LECTURE_ID = "lecture-01"
QUIZ_URL = f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/analytics/quiz-answer"
PREVIEW_HEADER = {"X-LecturePilot-Learner-Preview": "professor"}


def test_learner_overlay_quiz_is_visible_assessed_durable_and_isolated(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _install_overlay(client, "student-a", [_overlay_section("overlay-check", "overlay-quiz")])
    student_a = student_headers("student-a", course_ids=[COURSE_ID])

    canvas = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas",
        headers=student_a,
    )
    first = _submit(client, student_a, "overlay-attempt", "overlay-quiz", 1)
    replay = _submit(client, student_a, "overlay-attempt", "overlay-quiz", 1)
    student_b = _submit(
        client,
        student_headers("student-b", course_ids=[COURSE_ID]),
        "other-learner-attempt",
        "overlay-quiz",
        1,
    )
    preview = _submit(
        client,
        {**professor_headers("professor"), **PREVIEW_HEADER},
        "preview-attempt",
        "overlay-quiz",
        1,
    )

    assert canvas.status_code == 200
    assert _canvas_block(canvas.json(), "overlay-quiz")["text"] == "Which risk is minimized?"
    assert "answer_index" not in canvas.text
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert first.json()["correct"] is True
    assert first.json()["publication_version"] == 1
    assert "answer_index" not in first.text
    assert "correct_index" not in first.text
    assert _state(client, student_a)["overlay-quiz"]["selected_index"] == 1
    assert student_b.status_code == preview.status_code == 404
    assert _state(client, student_headers("student-b", course_ids=[COURSE_ID])) == {}
    events = client.app.state.analytics_store.events(course_id=COURSE_ID, lecture_id=LECTURE_ID)
    assert [(event["block_id"], event["attempt_index"]) for event in events] == [
        ("overlay-quiz", 1)
    ]


def test_legacy_compiled_learner_overlay_quiz_remains_assessable(tmp_path: Path) -> None:
    client = _client(tmp_path)
    workspace = client.app.state.canvas_workspace
    compiled_path = workspace.layout.legacy_compiled_canvas_path(
        "legacy-student", COURSE_ID, LECTURE_ID
    )
    compiled_path.parent.mkdir(parents=True)
    compiled_path.write_text(
        _document([_overlay_section("legacy-overlay", "legacy-overlay-quiz")]).model_dump_json(),
        encoding="utf-8",
    )

    response = _submit(
        client,
        student_headers("legacy-student", course_ids=[COURSE_ID]),
        "legacy-overlay-attempt",
        "legacy-overlay-quiz",
        1,
    )

    assert response.status_code == 200
    assert response.json()["correct"] is True
    assert response.json()["block_id"] == "legacy-overlay-quiz"


@pytest.mark.parametrize("stale_source", ["current_compiled", "legacy_compiled"])
def test_current_markdown_overlay_controls_visible_quiz_scoring(
    tmp_path: Path,
    stale_source: str,
) -> None:
    client = _client(tmp_path)
    _install_overlay(client, "student-a", [_overlay_section("shared", "visible-overlay-quiz")])
    _write_stale_overlay(client, "student-a", stale_source)
    headers = student_headers("student-a", course_ids=[COURSE_ID])

    hidden = _submit(
        client,
        headers,
        "hidden-stale-attempt",
        "hidden-stale-quiz",
        0,
    )
    visible = _submit(
        client,
        headers,
        "visible-current-attempt",
        "visible-overlay-quiz",
        1,
    )
    canvas = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas",
        headers=headers,
    )

    block_ids = {
        block["id"] for section in canvas.json()["sections"] for block in section["blocks"]
    }
    assert "visible-overlay-quiz" in block_ids
    assert "hidden-stale-quiz" not in block_ids
    assert hidden.status_code == 404
    assert visible.status_code == 200
    assert visible.json()["correct"] is True
    assert set(_state(client, headers)) == {"visible-overlay-quiz"}
    events = client.app.state.analytics_store.events(course_id=COURSE_ID, lecture_id=LECTURE_ID)
    assert [event["block_id"] for event in events] == ["visible-overlay-quiz"]


@pytest.mark.parametrize("collision", ["official", "overlay"])
def test_learner_overlay_quiz_collision_fails_before_state_or_analytics(
    tmp_path: Path,
    collision: str,
) -> None:
    client = _client(tmp_path)
    sections = (
        [_overlay_section("official-collision", "risk-quiz")]
        if collision == "official"
        else [
            _overlay_section("overlay-collision-a", "shared-overlay-quiz"),
            _overlay_section("overlay-collision-b", "shared-overlay-quiz"),
        ]
    )
    _install_overlay(client, "student-a", sections)
    headers = student_headers("student-a", course_ids=[COURSE_ID])

    response = _submit(client, headers, "collision-attempt", "risk-quiz", 1)

    expected_id = "risk-quiz" if collision == "official" else "shared-overlay-quiz"
    assert response.status_code == 409
    assert response.json()["detail"] == (f"Published canvas has duplicate quiz ID '{expected_id}'.")
    assert _state(client, headers) == {}
    assert client.app.state.analytics_store.events(course_id=COURSE_ID, lecture_id=LECTURE_ID) == []


def _submit(
    client: TestClient,
    headers: dict[str, str],
    attempt_id: str,
    quiz_id: str,
    option_index: int,
):
    return client.post(
        QUIZ_URL,
        headers=headers,
        json={
            "attendance": "present",
            "attempt_id": attempt_id,
            "block_id": quiz_id,
            "option_index": option_index,
        },
    )


def _state(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/learner-state",
        headers=headers,
    )
    assert response.status_code == 200
    return response.json()["quiz_states"]


def _install_overlay(client: TestClient, user_id: str, sections: list[CanvasSection]) -> None:
    client.app.state.canvas_workspace.apply_sections(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        user_id=user_id,
        sections=sections,
    )


def _write_stale_overlay(client: TestClient, user_id: str, source: str) -> None:
    layout = client.app.state.canvas_workspace.layout
    path = (
        layout.compiled_canvas_path(user_id, COURSE_ID, LECTURE_ID)
        if source == "current_compiled"
        else layout.legacy_compiled_canvas_path(user_id, COURSE_ID, LECTURE_ID)
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _document([_overlay_section("shared", "hidden-stale-quiz")]).model_dump_json(),
        encoding="utf-8",
    )


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
    app.state.canvas_workspace.write_course_canvas(_document([_official_section()]))
    return TestClient(app)


def _official_section() -> CanvasSection:
    return CanvasSection(
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


def _overlay_section(section_id: str, quiz_id: str) -> CanvasSection:
    return CanvasSection(
        id=f"student-{section_id}",
        title="Learner check",
        source_ref="student workspace",
        blocks=[
            CanvasBlock(
                id=quiz_id,
                type="quiz",
                text="Which risk is minimized?",
                items=["Posterior only", "Expected risk"],
                answer_index=1,
            )
        ],
    )


def _document(sections: list[CanvasSection]) -> CanvasDocument:
    return CanvasDocument(
        id=f"{COURSE_ID}-{LECTURE_ID}",
        import_version=CANVAS_IMPORT_VERSION,
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        title="Risk",
        source_kind="generated",
        source_ref="test source",
        workspace_path="course/index.md",
        sections=sections,
    )


def _canvas_block(payload: dict, block_id: str) -> dict:
    return next(
        block
        for section in payload["sections"]
        for block in section["blocks"]
        if block["id"] == block_id
    )
