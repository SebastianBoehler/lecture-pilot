from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_professor_reads_privacy_preserving_readiness_summary(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _create_course(client)

    for user_id, selected_index in (("student-a", 0), ("student-b", 1)):
        response = client.post(
            "/courses/demo-ml-course/exam-readiness/attempts",
            headers=student_headers(user_id),
            json={
                "answers": [
                    {"question_id": "lecture-03:risk-quiz", "selected_index": selected_index},
                    {"question_id": "lecture-03:risk:open", "text": "Expected risk weighs losses."},
                ]
            },
        )
        assert response.status_code == 200

    summary = client.get(
        "/admin/courses/demo-ml-course/exam-readiness/summary", headers=professor_headers()
    )

    assert summary.status_code == 200
    payload = summary.json()
    assert payload["course_id"] == "demo-ml-course"
    assert payload["total_attempts"] == 2
    assert payload["unique_learners"] == 2
    assert payload["task_status_counts"] == {"open": 3}
    assert payload["weak_sections"][0] == {
        "lecture_id": "lecture-03",
        "section_id": "risk",
        "open_tasks": 3,
    }
    assert "student-a" not in str(payload)
    assert "Expected risk weighs losses" not in str(payload)


def test_students_cannot_read_readiness_summary(tmp_path: Path) -> None:
    response = _client(tmp_path).get(
        "/admin/courses/demo-ml-course/exam-readiness/summary",
        headers=student_headers("student-a"),
    )

    assert response.status_code == 403


def test_readiness_summary_is_blank_without_attempts(tmp_path: Path) -> None:
    response = _client(tmp_path).get(
        "/admin/courses/demo-ml-course/exam-readiness/summary",
        headers=professor_headers(),
    )

    assert response.status_code == 200
    assert response.json()["total_attempts"] == 0


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    return TestClient(app)


def _create_course(client: TestClient) -> None:
    client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Demo ML Course",
            "target": "single-lecture",
            "lecture_number": "03",
            "lecture_title": "Risk",
        },
        headers=professor_headers(),
    )
    client.app.state.canvas_workspace.write_course_canvas(
        CanvasDocument(
            id="demo-ml-course-lecture-03",
            course_id="demo-ml-course",
            lecture_id="lecture-03",
            title="Risk",
            source_kind="generated",
            source_ref="lecture-03.tex",
            workspace_path="course/canvas/index.md",
            sections=[
                CanvasSection(
                    id="risk",
                    title="Risk",
                    source_ref="lecture-03.tex",
                    blocks=[
                        CanvasBlock(
                            id="risk-quiz",
                            type="quiz",
                            text="Which quantity should be minimized?",
                            items=["Posterior only", "Expected risk"],
                            answer_index=1,
                        ),
                        CanvasBlock(
                            id="risk-text", type="paragraph", text="Expected risk weighs losses."
                        ),
                    ],
                )
            ],
        )
    )
