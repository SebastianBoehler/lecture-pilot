import json
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_legacy_publication_remains_manageable_but_unavailable(tmp_path: Path) -> None:
    client = legacy_client(tmp_path)
    response = client.get("/admin/courses", headers=professor_headers())

    assert response.status_code == 200
    workspace = response.json()[0]
    assert workspace["legacy_lecture_ids"] == ["lecture-03"]
    assert workspace["published_lecture_ids"] == []
    assert workspace["access_summary"]["lectures"][0]["content_ready"] is False
    assert workspace["course"]["access_policy"] == "instructors_only"
    student = student_headers(course_ids=("demo-ml-course",))
    assert "demo-ml-course" not in {c["id"] for c in client.get("/courses", headers=student).json()}
    assert client.delete("/admin/courses/demo-ml-course", headers=student).status_code == 403
    deleted = client.delete("/admin/courses/demo-ml-course", headers=professor_headers())
    assert deleted.status_code == 200
    assert client.get("/admin/courses", headers=professor_headers()).json() == []


def test_corrupt_metadata_is_not_mislabeled_as_legacy(tmp_path: Path) -> None:
    client = legacy_client(tmp_path)
    path = client.app.state.canvas_workspace.course_canvas_store.path(
        "demo-ml-course", "lecture-03"
    )
    (path / "publication.json").write_text("{}")
    response = client.get("/admin/courses", headers=professor_headers())
    assert response.status_code == 200
    assert response.json()[0]["legacy_lecture_ids"] == []
    assert response.json()[0]["published_lecture_ids"] == []


def legacy_client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    client = TestClient(app, raise_server_exceptions=False)
    result = client.post(
        "/admin/course-workspaces",
        headers=professor_headers(),
        json={
            "course_title": "Demo ML Course",
            "lecture_number": "03",
            "lecture_title": "Bayesian Decision Theory",
            "target": "single-lecture",
            "access_policy": "instructors_only",
        },
    )
    assert result.status_code == 200
    path = app.state.canvas_workspace.course_canvas_store.path("demo-ml-course", "lecture-03")
    path.mkdir(parents=True)
    (path / "index.md").write_text("Legacy content")
    (path / "learning-map.json").write_text("{}")
    (path / "publication.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "course_id": "demo-ml-course",
                "lecture_id": "lecture-03",
                "version": 1,
                "published_at": "2026-07-22T19:28:28Z",
                "published_by": "prof-demo",
                "source_draft_path": "canvas-drafts/lectures/lecture-03/latest",
                "published_path": "canvas/lectures/lecture-03",
            }
        )
    )
    return client
