from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import confirm_source_routing, professor_headers
from lecturepilot.app import create_app
from lecturepilot.canvas.canvas_workspace import CanvasWorkspace


COURSE_ID = "practice-course"


def client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "course"
    )
    test_client = TestClient(app)
    created = test_client.post(
        "/admin/course-workspaces",
        headers=professor_headers(),
        json={
            "course_title": "Practice Course",
            "target": "full-course",
            "replace_lectures": True,
            "lectures": [
                {
                    "number": "01",
                    "title": "Practice lecture",
                    "date": "2026-07-01",
                    "material_path": "Lecture01.md",
                }
            ],
        },
    )
    assert created.status_code == 200
    response = test_client.post(
        f"/admin/courses/{COURSE_ID}/materials",
        headers=professor_headers(),
        data={"path": "Lecture01.md"},
        files={
            "file": (
                "Lecture01.md",
                b"# Bayes rule\n\nBayes rule maps prior probabilities and likelihood evidence into posterior probabilities.",
            )
        },
    )
    assert response.status_code == 200
    confirm_source_routing(test_client, COURSE_ID)
    return test_client


def design_path() -> str:
    return f"/admin/courses/{COURSE_ID}/lectures/lecture-01/practice-design"
