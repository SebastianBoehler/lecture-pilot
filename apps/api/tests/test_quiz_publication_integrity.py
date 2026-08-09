from concurrent.futures import ThreadPoolExecutor
from datetime import date
import json
from pathlib import Path
import shutil
from threading import Event

import pytest
from fastapi.testclient import TestClient

from auth_helpers import student_headers
from lecturepilot import course_canvas_store as course_canvas_store_module
from lecturepilot.app import create_app
from lecturepilot.canvas_markdown import write_document_source
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_canvas_store import CourseCanvasStore, InvalidCanvasDraftError
from lecturepilot.course_learning_design_store import CourseLearningDesignStore
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.learning_map import build_learning_map
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture
from lecturepilot.storage_layout import StorageLayout


COURSE_ID = "quiz-snapshot"
LECTURE_ID = "lecture-01"
QUIZ_URL = f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/analytics/quiz-answer"


def test_quiz_submission_scores_document_and_version_from_one_published_snapshot(
    tmp_path: Path, monkeypatch
) -> None:
    client = _client(tmp_path, _quiz_document(answer_index=0, question="Version one"))
    store = client.app.state.canvas_workspace.course_canvas_store
    published_dir = store.path(COURSE_ID, LECTURE_ID)
    original_read = course_canvas_store_module.read_document_source
    document_read = Event()
    release_read = Event()
    publication_finished = Event()

    def controlled_read(path: Path) -> CanvasDocument:
        document = original_read(path)
        if path.resolve() == published_dir.resolve():
            document_read.set()
            assert release_read.wait(timeout=3)
        return document

    original_publication = client.app.state.canvas_workspace.course_canvas_publication

    def publication_after_republish(**kwargs):
        assert publication_finished.wait(timeout=3)
        return original_publication(**kwargs)

    monkeypatch.setattr(course_canvas_store_module, "read_document_source", controlled_read)
    monkeypatch.setattr(
        client.app.state.canvas_workspace,
        "course_canvas_publication",
        publication_after_republish,
    )

    def republish() -> dict:
        result = _publish(
            client,
            _quiz_document(answer_index=1, question="Version two"),
        )
        publication_finished.set()
        return result

    with ThreadPoolExecutor(max_workers=2) as executor:
        answer = executor.submit(_submit, client, "snapshot-attempt", 0)
        assert document_read.wait(timeout=3)
        publication = executor.submit(republish)
        assert not publication_finished.wait(timeout=0.2)
        release_read.set()
        response = answer.result(timeout=3)
        assert publication.result(timeout=3)["version"] == 2

    assert response.status_code == 200
    assert response.json()["correct"] is True
    assert response.json()["publication_version"] == 1
    assert _state(client) == {}


def test_duplicate_canonical_quiz_ids_are_rejected_by_all_canvas_writes(
    tmp_path: Path,
) -> None:
    document = _duplicate_quiz_document()

    with pytest.raises(ValueError, match="Duplicate canonical quiz ID 'shared-quiz'"):
        build_learning_map(document)

    store = CourseCanvasStore(StorageLayout(tmp_path / "workspaces"))
    with pytest.raises(ValueError, match="Duplicate canonical quiz ID 'shared-quiz'"):
        store.write(document)
    with pytest.raises(InvalidCanvasDraftError, match="invalid and was not saved"):
        store.write_draft(document)

    draft_dir = store.draft_path(COURSE_ID, LECTURE_ID)
    write_document_source(document, draft_dir)
    with pytest.raises(InvalidCanvasDraftError, match="Stored canvas draft is invalid"):
        store.publish_draft(
            course_id=COURSE_ID,
            lecture_id=LECTURE_ID,
            published_by="professor",
        )


def test_duplicate_legacy_quiz_ids_fail_closed_without_state_or_analytics(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path, _quiz_document(answer_index=0, question="Initial"))
    store = client.app.state.canvas_workspace.course_canvas_store
    published_dir = store.path(COURSE_ID, LECTURE_ID)
    shutil.rmtree(published_dir)
    write_document_source(_duplicate_quiz_document(), published_dir)
    (published_dir / "publication.json").write_text(json.dumps({"version": 1}), encoding="utf-8")

    response = _submit(client, "ambiguous-attempt", 0)

    assert response.status_code == 409
    assert response.json()["detail"] == "Published canvas has duplicate quiz ID 'shared-quiz'."
    assert _state(client) == {}
    assert client.app.state.analytics_store.events(course_id=COURSE_ID, lecture_id=LECTURE_ID) == []


def _submit(
    client: TestClient,
    attempt_id: str,
    option_index: int,
    *,
    quiz_id: str = "risk-quiz",
):
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


def _client(tmp_path: Path, document: CanvasDocument) -> TestClient:
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
    _publish(client, document)
    return client


def _publish(client: TestClient, document: CanvasDocument) -> dict:
    workspace = client.app.state.canvas_workspace
    manifest = workspace.layout.lecture_source_manifest_path(COURSE_ID, LECTURE_ID)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        '{"course_id":"quiz-snapshot","lecture_id":"lecture-01",'
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
    return workspace.publish_course_canvas_draft(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        published_by="professor",
    )


def _quiz_document(*, answer_index: int, question: str) -> CanvasDocument:
    return _document(
        [
            CanvasSection(
                id="risk",
                title="Risk",
                blocks=[
                    CanvasBlock(
                        id="risk-quiz",
                        type="quiz",
                        text=question,
                        items=["Posterior only", "Expected risk"],
                        answer_index=answer_index,
                    )
                ],
            )
        ]
    )


def _duplicate_quiz_document() -> CanvasDocument:
    first = _component_section("concept-a", "quiz-shell-a")
    first.blocks.append(
        CanvasBlock(
            id="risk-quiz",
            type="quiz",
            text="This distinct quiz must also fail closed.",
            items=["A", "B"],
            answer_index=0,
        )
    )
    return _document(
        [
            first,
            _component_section("concept-b", "quiz-shell-b"),
        ]
    )


def _component_section(section_id: str, block_id: str) -> CanvasSection:
    return CanvasSection(
        id=section_id,
        title=section_id,
        blocks=[
            CanvasBlock(
                id=block_id,
                type="component",
                component_id="shared-quiz",
                component_type="single_choice_quiz",
                text="Choose one.",
                items=["A", "B"],
                answer_index=0,
            )
        ],
    )


def _document(sections: list[CanvasSection]) -> CanvasDocument:
    return CanvasDocument(
        id=f"{COURSE_ID}-{LECTURE_ID}",
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        title="Risk",
        source_kind="generated",
        source_ref="test source",
        workspace_path="course/index.md",
        sections=sections,
    )
