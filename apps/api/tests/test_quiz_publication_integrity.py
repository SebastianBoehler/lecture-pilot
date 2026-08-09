from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from auth_helpers import student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_canvas_store import InvalidCanvasDraftError
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.learning_map import build_learning_map
from lecturepilot.models import Course, CourseWorkspaceResult, Lecture
from canvas_workspace_fixtures import (
    configure_canvas_workspace,
    publish_course_canvas,
    write_canvas_draft,
)


COURSE_ID = "quiz-snapshot"
LECTURE_ID = "lecture-01"
QUIZ_URL = f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/analytics/quiz-answer"


def test_quiz_submission_scores_document_and_version_from_one_published_snapshot(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path, _quiz_document(answer_index=0, question="Version one"))
    documents = [
        _quiz_document(
            answer_index=0 if version % 2 else 1,
            question=f"Version {version}",
        )
        for version in range(2, 10)
    ]
    start_round = Barrier(2)
    end_round = Barrier(2)

    def publish_all() -> None:
        for document in documents:
            start_round.wait()
            _publish(client, document)
            end_round.wait()

    observed: list[tuple[int, bool | None]] = []
    stale_responses = 0
    with ThreadPoolExecutor(max_workers=1) as executor:
        publication = executor.submit(publish_all)
        for attempt, _document in enumerate(documents, start=1):
            version = _publication_version(client)
            start_round.wait()
            response = _submit(
                client,
                f"snapshot-attempt-{attempt}",
                0,
                publication_version=version,
            )
            end_round.wait()
            assert response.status_code in {200, 409}
            if response.status_code == 409:
                stale_responses += 1
                assert response.json()["detail"]["code"] == "stale_quiz_publication"
            else:
                payload = response.json()
                observed.append((payload["publication_version"], payload["correct"]))
        publication.result(timeout=20)

    assert observed or stale_responses
    assert all(correct is (version % 2 == 1) for version, correct in observed)


def test_duplicate_canonical_quiz_ids_are_rejected_by_all_canvas_writes(
    tmp_path: Path,
) -> None:
    document = _duplicate_quiz_document()

    with pytest.raises(ValueError, match="Duplicate canonical quiz ID 'shared-quiz'"):
        build_learning_map(document)

    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    with pytest.raises(InvalidCanvasDraftError, match="invalid and was not saved"):
        write_canvas_draft(workspace, document)


def _submit(
    client: TestClient,
    attempt_id: str,
    option_index: int,
    *,
    publication_version: int,
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
            "publication_version": publication_version,
        },
    )


def _publication_version(client: TestClient) -> int:
    response = client.get(
        f"/courses/{COURSE_ID}/lectures/{LECTURE_ID}/learner-state",
        headers=student_headers("student-a", course_ids=[COURSE_ID]),
    )
    assert response.status_code == 200
    return response.json()["publication_version"]


def _client(tmp_path: Path, document: CanvasDocument) -> TestClient:
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
                Lecture(id=LECTURE_ID, course_id=COURSE_ID, title="Risk", date=date(2020, 1, 1))
            ],
            active_lecture_id=LECTURE_ID,
        ),
    )
    client = TestClient(app)
    _publish(client, document)
    return client


def _publish(client: TestClient, document: CanvasDocument) -> dict:
    return publish_course_canvas(client.app.state.canvas_workspace, document)


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
