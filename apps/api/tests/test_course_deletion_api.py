from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_professor_lists_created_course_workspaces(tmp_path: Path) -> None:
    client = _client(tmp_path)
    empty = client.get("/admin/courses", headers=professor_headers())
    _create_workspace(client)

    response = client.get("/admin/courses", headers=professor_headers())

    assert empty.status_code == 200
    assert empty.json() == []
    assert response.status_code == 200
    assert response.json()[0]["course"]["id"] == "demo-ml-course"
    assert response.json()[0]["lectures"][0]["id"] == "lecture-03"


def test_student_cannot_list_created_course_workspaces(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get("/admin/courses", headers=student_headers("student01"))

    assert response.status_code == 403


def test_professor_deletes_created_course_workspace(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _create_workspace(client)
    course_root = client.app.state.canvas_workspace.layout.course_root("demo-ml-course")
    (course_root / "source" / "uploads").mkdir(parents=True)
    (course_root / "source" / "uploads" / "Lecture03.tex").write_text("source", encoding="utf-8")

    response = client.delete("/admin/courses/demo-ml-course", headers=professor_headers())
    courses = client.get("/courses", headers=student_headers("student01"))
    lectures = client.get("/courses/demo-ml-course/lectures", headers=student_headers("student01"))

    assert response.status_code == 200
    assert response.json()["archived"] is True
    assert not course_root.exists()
    assert "demo-ml-course" not in {course["id"] for course in courses.json()}
    assert lectures.status_code == 404


def test_student_cannot_delete_course_workspace(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _create_workspace(client)

    response = client.delete("/admin/courses/demo-ml-course", headers=student_headers("student01"))

    assert response.status_code == 403


def test_course_deletion_rejects_invalid_course_id(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.delete("/admin/courses/...", headers=professor_headers())

    assert response.status_code == 400


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    return TestClient(app)


def _create_workspace(client: TestClient) -> None:
    response = client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Demo ML Course",
            "lecture_number": "03",
            "lecture_title": "Bayesian Decision Theory",
            "target": "single-lecture",
        },
        headers=professor_headers("prof-demo"),
    )
    assert response.status_code == 200
