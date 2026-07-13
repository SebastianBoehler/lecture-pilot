from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_single_lecture_workspace_update_keeps_existing_course_schedule(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Demo ML Course",
            "target": "full-course",
            "lectures": [
                {"number": "01", "title": "Overview", "date": "2026-05-06"},
                {"number": "02", "title": "Generalization", "date": "2026-05-13"},
            ],
        },
        headers=professor_headers(),
    )
    assert response.status_code == 200

    response = client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Demo ML Course",
            "target": "single-lecture",
            "lecture_number": "01",
            "lecture_title": "Updated Overview",
        },
        headers=professor_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_lecture_id"] == "lecture-01"
    assert [lecture["id"] for lecture in payload["lectures"]] == ["lecture-01", "lecture-02"]
    assert payload["lectures"][0]["title"] == "Updated Overview"
    assert payload["lectures"][1]["title"] == "Generalization"

    lectures = client.get("/courses/demo-ml-course/lectures", headers=student_headers())
    assert [item["lecture"]["id"] for item in lectures.json()] == ["lecture-01", "lecture-02"]


def test_sparse_single_lecture_update_keeps_existing_material_mapping(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Demo ML Course",
            "target": "full-course",
            "lectures": [
                {
                    "number": "03",
                    "title": "Bayesian Decision Theory and Naive Bayes",
                    "date": "2026-05-20",
                    "material_path": "Lecture03-eng.tex",
                },
            ],
        },
        headers=professor_headers(),
    )
    assert response.status_code == 200

    response = client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Demo ML Course",
            "target": "single-lecture",
            "lecture_number": "03",
            "lecture_title": "Bayesian Decision Theory",
        },
        headers=professor_headers(),
    )

    assert response.status_code == 200
    lecture = response.json()["lectures"][0]
    assert lecture["title"] == "Bayesian Decision Theory and Naive Bayes"
    assert lecture["material_path"] == "Lecture03-eng.tex"


def test_full_course_schedule_can_replace_inferred_lectures(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Demo ML Course",
            "target": "full-course",
            "lectures": [
                {"number": "01", "title": "Overview", "date": "2026-05-06"},
                {"number": "02", "title": "Generalization", "date": "2026-05-13"},
            ],
        },
        headers=professor_headers(),
    )
    assert response.status_code == 200

    response = client.post(
        "/admin/course-workspaces",
        json={
            "course_id": "demo-ml-course",
            "course_title": "Demo ML Course",
            "target": "full-course",
            "replace_lectures": True,
            "lectures": [
                {"number": "01", "title": "Overview", "date": "2026-05-06"},
            ],
        },
        headers=professor_headers(),
    )

    assert response.status_code == 200
    assert [lecture["id"] for lecture in response.json()["lectures"]] == ["lecture-01"]


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    return TestClient(app)
