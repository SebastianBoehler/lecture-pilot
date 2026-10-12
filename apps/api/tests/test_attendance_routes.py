from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import student_headers
from canvas_workspace_fixtures import publish_course_canvas, published_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    material_root = tmp_path / "materials"
    material_root.mkdir()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=material_root
    )
    (material_root / "Lecture01-eng.tex").write_text(
        "\\begin{frame}{Setup}Setup\\end{frame}", encoding="utf-8"
    )
    publish_course_canvas(
        app.state.canvas_workspace, published_course_canvas("martius-ml", "lecture-01")
    )
    return TestClient(app)


def _attendance(client: TestClient, user: str) -> str:
    lectures = client.get("/courses/martius-ml/lectures", headers=student_headers(user)).json()
    return next(item["attendance"] for item in lectures if item["lecture"]["id"] == "lecture-01")


def test_marked_attendance_survives_reload_and_stays_private(tmp_path: Path) -> None:
    client = _client(tmp_path)
    assert _attendance(client, "student01") == "unknown"

    response = client.put(
        "/courses/martius-ml/lectures/lecture-01/attendance",
        json={"attendance": "present"},
        headers=student_headers("student01"),
    )

    assert response.status_code == 200
    assert response.json() == {"lecture_id": "lecture-01", "attendance": "present"}
    assert _attendance(client, "student01") == "present"
    assert _attendance(client, "student02") == "unknown"


def test_attendance_rejects_unknown_lectures_and_values(tmp_path: Path) -> None:
    client = _client(tmp_path)
    headers = student_headers("student01")

    missing = client.put(
        "/courses/martius-ml/lectures/lecture-99/attendance",
        json={"attendance": "present"},
        headers=headers,
    )
    invalid = client.put(
        "/courses/martius-ml/lectures/lecture-01/attendance",
        json={"attendance": "maybe"},
        headers=headers,
    )

    assert missing.status_code == 404
    assert invalid.status_code == 422
