from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from canvas_workspace_fixtures import publish_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.ppi_exam_source_store import PpiExamSourceStore
from lecturepilot.practice_exam_generation_jobs import PracticeExamGenerationStore
from lecturepilot.practice_exam_models import PracticeExam, PracticeExamQuestion
from lecturepilot.practice_exam_store import PracticeExamStore


def test_generation_returns_public_exam_and_replays_idempotently(tmp_path: Path) -> None:
    client, planner = _client(tmp_path)

    first = _generate(client)
    replay = _generate(client)

    assert first.status_code == 200
    assert replay.status_code == 200
    assert first.json() == replay.json()
    assert planner.calls == 1
    assert first.headers["X-Generation-Id"] == replay.headers["X-Generation-Id"]
    assert len(first.json()["questions"]) == 20
    assert "answer_index" not in first.text
    assert "rubric" not in first.text
    assert "reference_answer" not in first.text
    assert "source_ids" not in first.text
    assert "ppi_source_ids" not in first.text


def test_generation_accepts_comprehensive_50_question_exam(tmp_path: Path) -> None:
    client, _planner = _client(tmp_path)

    response = _generate(
        client,
        question_count=50,
        key="practice-exam-key-comprehensive-0001",
    )

    assert response.status_code == 200
    assert len(response.json()["questions"]) == 50


def test_generation_uses_only_published_unlocked_canvas_and_selected_private_source(
    tmp_path: Path,
) -> None:
    client, planner = _client(tmp_path)
    source = client.app.state.ppi_exam_source_store.import_archive(
        user_id="student-a",
        course_id="martius-ml",
        lecture_id=42,
        title="Machine Learning",
        protocol_count=7,
        filename="protocols.zip",
        archive=_archive(),
    )

    response = _generate(client, ppi_source_ids=[source.id], key="practice-exam-key-0002")

    assert response.status_code == 200
    assert [item.lecture_id for item in planner.documents] == ["lecture-01"]
    assert planner.ppi_sources == {"ppi-42": ["Typical old exam pattern."]}


def test_generation_rejects_unowned_source_and_professor(tmp_path: Path) -> None:
    client, planner = _client(tmp_path)
    missing = _generate(client, ppi_source_ids=["ppi-42"])
    professor = client.post(
        "/courses/martius-ml/practice-exam-generations",
        headers={**professor_headers(), "Idempotency-Key": "practice-exam-key-professor"},
        json={"question_count": 20, "duration_minutes": 90, "ppi_source_ids": []},
    )

    assert missing.status_code == 404
    assert missing.json()["detail"] == "Selected PPI source was not found."
    assert professor.status_code == 403
    assert planner.calls == 0


def test_generation_failure_is_recoverable_and_exposes_safe_status(tmp_path: Path) -> None:
    client, planner = _client(tmp_path)
    planner.error = ModelExecutionError("provider included private prompt")

    response = _generate(client)
    status = client.get(
        "/courses/martius-ml/practice-exam-generations/status",
        headers={
            **student_headers("student-a"),
            "Idempotency-Key": "practice-exam-key-0001",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Practice exam generation failed. Please retry."
    assert "private prompt" not in response.text
    assert status.status_code == 200
    assert status.json()["status"] == "failed"
    assert status.json()["error_code"] == "model_execution_error"


def test_unexpected_generation_failure_releases_the_job_lease(tmp_path: Path) -> None:
    client, planner = _client(tmp_path, raise_server_exceptions=False)
    planner.error = RuntimeError("unexpected private provider detail")

    response = _generate(client)
    status = client.get(
        "/courses/martius-ml/practice-exam-generations/status",
        headers={
            **student_headers("student-a"),
            "Idempotency-Key": "practice-exam-key-0001",
        },
    )

    assert response.status_code == 500
    assert "private provider detail" not in response.text
    assert status.json()["status"] == "failed"
    assert status.json()["error_code"] == "unexpected_error"


def test_exam_library_read_and_delete_are_learner_private(tmp_path: Path) -> None:
    client, _planner = _client(tmp_path)
    generated = _generate(client).json()
    exam_id = generated["id"]

    listed = client.get("/courses/martius-ml/practice-exams", headers=student_headers("student-a"))
    read = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}", headers=student_headers("student-a")
    )
    other = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}", headers=student_headers("student-b")
    )
    deleted = client.delete(
        f"/courses/martius-ml/practice-exams/{exam_id}", headers=student_headers("student-a")
    )

    assert [item["id"] for item in listed.json()] == [exam_id]
    assert read.json() == generated
    assert other.status_code == 404
    assert deleted.json() == {"deleted": True}
    assert (
        client.get(
            f"/courses/martius-ml/practice-exams/{exam_id}", headers=student_headers("student-a")
        ).status_code
        == 404
    )


def test_solution_sheet_is_separate_and_learner_private(tmp_path: Path) -> None:
    client, _planner = _client(tmp_path)
    generated = _generate(client).json()
    exam_id = generated["id"]

    own = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}/solutions",
        headers=student_headers("student-a"),
    )
    other = client.get(
        f"/courses/martius-ml/practice-exams/{exam_id}/solutions",
        headers=student_headers("student-b"),
    )

    assert own.status_code == 200
    assert own.json()["exam_id"] == exam_id
    assert own.json()["questions"][0]["answer_index"] == 1
    assert own.json()["questions"][1]["reference_answer"] == (
        "Empirical risk averages observed loss and applies it to the stated decision."
    )
    assert "source_ids" not in own.text
    assert other.status_code == 404


def _generate(
    client: TestClient,
    *,
    question_count: int = 20,
    ppi_source_ids: list[str] | None = None,
    key: str = "practice-exam-key-0001",
):
    return client.post(
        "/courses/martius-ml/practice-exam-generations",
        headers={**student_headers("student-a"), "Idempotency-Key": key},
        json={
            "question_count": question_count,
            "duration_minutes": 90,
            "ppi_source_ids": ppi_source_ids or [],
        },
    )


def _client(
    tmp_path: Path, *, raise_server_exceptions: bool = True
) -> tuple[TestClient, "_Planner"]:
    app = create_app()
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    publish_course_canvas(workspace, _document())
    app.state.canvas_workspace = workspace
    app.state.practice_exam_store = PracticeExamStore(workspace.layout)
    app.state.practice_exam_generation_store = PracticeExamGenerationStore(
        workspace.layout, lease_seconds=30
    )
    app.state.ppi_exam_source_store = PpiExamSourceStore(workspace.layout)
    planner = _Planner()
    app.state.practice_exam_planner = planner
    return TestClient(app, raise_server_exceptions=raise_server_exceptions), planner


class _Planner:
    def __init__(self) -> None:
        self.calls = 0
        self.error: Exception | None = None
        self.documents: list[CanvasDocument] = []
        self.ppi_sources: dict[str, list[str]] = {}

    async def plan(self, **kwargs) -> PracticeExam:
        self.calls += 1
        if self.error:
            raise self.error
        self.documents = kwargs["documents"]
        self.ppi_sources = kwargs["ppi_sources"]
        questions = [
            PracticeExamQuestion(
                id=f"q-{index:02d}",
                kind="multiple_choice" if index % 2 else "open_ended",
                prompt=f"Question {index}: apply empirical risk?",
                points=2,
                difficulty="standard",
                options=["A", "B", "C", "D"] if index % 2 else [],
                answer_index=1 if index % 2 else None,
                rubric=[] if index % 2 else ["Defines risk", "Applies risk"],
                reference_answer=(
                    None
                    if index % 2
                    else "Empirical risk averages observed loss and applies it to the stated decision."
                ),
                source_ids=["lecture-01:risk:definition"],
                ppi_pattern_ids=[],
            )
            for index in range(1, kwargs["question_count"] + 1)
        ]
        return PracticeExam(
            id="a" * 32,
            course_id=kwargs["course_id"],
            title="Machine Learning practice exam",
            language=kwargs["language"],
            instructions=["Answer every question."],
            duration_minutes=kwargs["duration_minutes"],
            created_at=datetime.now(UTC),
            total_points=sum(item.points for item in questions),
            source_revision="b" * 64,
            source_ids=["lecture-01:risk:definition"],
            ppi_source_ids=sorted(kwargs["ppi_sources"]),
            questions=questions,
        )


def _document() -> CanvasDocument:
    return CanvasDocument(
        id="canvas-1",
        course_id="martius-ml",
        lecture_id="lecture-01",
        title="Risk minimization",
        source_kind="markdown",
        source_ref="lecture-01.md",
        workspace_path="canvas/lectures/lecture-01/index.md",
        sections=[
            CanvasSection(
                id="risk",
                title="Empirical risk",
                blocks=[
                    CanvasBlock(
                        id="definition",
                        type="paragraph",
                        text="Empirical risk averages the observed training loss.",
                    )
                ],
            )
        ],
    )


def _archive() -> bytes:
    content = BytesIO()
    with ZipFile(content, "w") as bundle:
        bundle.writestr("questions.txt", "Typical old exam pattern.")
    return content.getvalue()
