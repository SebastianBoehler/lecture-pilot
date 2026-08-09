import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from canvas_workspace_fixtures import publish_course_canvas
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.coaching_orchestration import prepare_coaching_turn
from lecturepilot.course_canvas_context import InvalidPublishedCanvasContextError
from lecturepilot.guided_tutor import LOCAL_PREVIEW_USER_ID
from lecturepilot.models import AgentTurnInput, AttendanceStatus
from lecturepilot.observability import Observability
from test_quiz_learner_overlay import (
    COURSE_ID,
    LECTURE_ID,
    _client,
    _document,
    _overlay_section,
    _submit,
)


def test_compiled_overlay_quizzes_are_never_visible_or_assessable(tmp_path: Path) -> None:
    client = _client(tmp_path)
    workspace = client.app.state.canvas_workspace
    user_id = "student-a"
    headers = student_headers(user_id, course_ids=[COURSE_ID])
    workspace.apply_sections(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        user_id=user_id,
        sections=[_overlay_section("markdown", "markdown-quiz")],
    )
    current = workspace.layout.user_lecture_root(user_id, COURSE_ID, LECTURE_ID) / "canvas.json"
    old = (
        workspace.layout.root
        / "workspaces"
        / "students"
        / workspace.layout.user_key(user_id)
        / "courses"
        / COURSE_ID
        / "lectures"
        / LECTURE_ID
        / "canvas.json"
    )
    _write_compiled_quiz(current, "compiled-current", "compiled-current-quiz")
    _write_compiled_quiz(old, "compiled-old", "compiled-old-quiz")

    canvas = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas",
        headers=headers,
    )
    current_answer = _submit(client, headers, "compiled-current", "compiled-current-quiz", 1)
    old_answer = _submit(client, headers, "compiled-old", "compiled-old-quiz", 1)
    markdown_answer = _submit(client, headers, "markdown", "markdown-quiz", 1)

    assert canvas.status_code == 200
    block_ids = {
        block["id"]
        for section in canvas.json()["document"]["sections"]
        for block in section["blocks"]
    }
    assert "compiled-current-quiz" not in block_ids
    assert "compiled-old-quiz" not in block_ids
    assert "markdown-quiz" in block_ids
    assert current_answer.status_code == old_answer.status_code == 404
    assert markdown_answer.status_code == 200


def test_snapshot_exposes_one_strict_typed_publication_contract(tmp_path: Path) -> None:
    client = _client(tmp_path)
    snapshot = (
        client.app.state.canvas_workspace.course_canvas_store.read_current_published_snapshot(
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
        )
    )

    assert snapshot is not None
    assert snapshot.publication.course_id == COURSE_ID
    assert snapshot.publication.lecture_id == LECTURE_ID
    assert snapshot.publication.version == snapshot.version == 1
    assert snapshot.publication.learning_map_revision == snapshot.learning_map.revision
    assert snapshot.publication.source_revision
    assert snapshot.publication.draft_digest
    assert snapshot.publication.published_at.tzinfo is not None
    assert snapshot.publication.published_by == "professor"


def test_draft_write_requires_the_captured_source_revision(tmp_path: Path) -> None:
    client = _client(tmp_path)

    with pytest.raises(TypeError):
        client.app.state.canvas_workspace.write_course_canvas_draft(_document([]))


def test_local_preview_uses_the_same_published_gate_and_version_contract(tmp_path: Path) -> None:
    client = _client(tmp_path)
    publish_course_canvas(
        client.app.state.canvas_workspace,
        _document(
            [
                CanvasSection(
                    id="strict-section",
                    title="Strict section",
                    blocks=[
                        CanvasBlock(
                            id="strict-gate",
                            type="checkpoint",
                            text="Explain the published mechanism.",
                        )
                    ],
                )
            ]
        ),
    )

    prepared = prepare_coaching_turn(
        client.app,
        AgentTurnInput(
            user_id=LOCAL_PREVIEW_USER_ID,
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
            attendance=AttendanceStatus.PRESENT,
            message="Check me.",
        ),
        lambda _tag: None,
        Observability(),
    )

    assert prepared.active_gate is not None
    assert prepared.active_gate.id == "strict-gate"
    assert prepared.analytics_context is not None
    assert prepared.analytics_context.publication_version == 2


@pytest.mark.parametrize(
    "corruption",
    [
        "bare_index",
        "extra_metadata",
        "coerced_metadata",
        "missing_map",
        "coerced_map",
        "map_mismatch",
    ],
)
def test_invalid_publication_is_rejected_at_every_consumer_boundary(
    tmp_path: Path,
    corruption: str,
) -> None:
    seeded = _client(tmp_path)
    workspace = seeded.app.state.canvas_workspace
    if corruption == "coerced_map":
        publish_course_canvas(
            workspace,
            _document(
                [
                    CanvasSection(
                        id="strict-section",
                        title="Strict section",
                        blocks=[
                            CanvasBlock(
                                id="strict-checkpoint",
                                type="checkpoint",
                                text="Explain the strict contract.",
                            )
                        ],
                    )
                ]
            ),
        )
    publication = workspace.course_canvas_store.publication(
        course_id=COURSE_ID, lecture_id=LECTURE_ID
    )
    expected_version = publication.version if publication is not None else 1
    published_dir = workspace.course_canvas_store.path(COURSE_ID, LECTURE_ID)
    _corrupt_publication(published_dir, corruption)
    client = TestClient(seeded.app, raise_server_exceptions=False)
    student = student_headers("student-a", course_ids=[COURSE_ID])

    responses = [
        client.get(f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/canvas", headers=student),
        client.get(f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/learner-state", headers=student),
        client.get(f"/courses/{COURSE_ID}/review-queue", headers=student),
        client.post(
            f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/analytics/quiz-answer",
            headers=student,
            json={
                "attendance": "present",
                "attempt_id": f"corrupt-{corruption}",
                "block_id": "risk-quiz",
                "option_index": 1,
                "publication_version": expected_version,
            },
        ),
        client.get(
            f"/admin/courses/{COURSE_ID}/lectures/{LECTURE_ID}/analytics",
            headers=professor_headers("professor"),
        ),
    ]

    assert [response.status_code for response in responses] == [409, 409, 409, 409, 409]
    with pytest.raises(InvalidPublishedCanvasContextError):
        prepare_coaching_turn(
            seeded.app,
            AgentTurnInput(
                user_id="student-a",
                course_id=COURSE_ID,
                lecture_id=LECTURE_ID,
                attendance=AttendanceStatus.PRESENT,
                message="Check my answer.",
            ),
            lambda _tag: None,
            Observability(),
        )


def _write_compiled_quiz(path: Path, section_id: str, quiz_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = _document(
        [
            CanvasSection(
                id=f"student-{section_id}",
                title="Compiled check",
                source_ref="student workspace",
                blocks=[
                    CanvasBlock(
                        id=quiz_id,
                        type="quiz",
                        text="Compiled question",
                        items=["A", "B"],
                        answer_index=1,
                    )
                ],
            )
        ]
    )
    path.write_text(document.model_dump_json(), encoding="utf-8")


def _corrupt_publication(published_dir: Path, corruption: str) -> None:
    metadata_path = published_dir / "publication.json"
    map_path = published_dir / "learning-map.json"
    if corruption == "bare_index":
        metadata_path.unlink()
        map_path.unlink()
        return
    if corruption == "missing_map":
        map_path.unlink()
        return
    if corruption == "coerced_map":
        learning_map = json.loads(map_path.read_text(encoding="utf-8"))
        learning_map["gates"][0]["review_after_days"] = "2"
        map_path.write_text(json.dumps(learning_map), encoding="utf-8")
        return
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if corruption == "extra_metadata":
        metadata["unexpected"] = True
    elif corruption == "coerced_metadata":
        metadata["version"] = "1"
    else:
        metadata["learning_map_revision"] = "f" * 64
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
