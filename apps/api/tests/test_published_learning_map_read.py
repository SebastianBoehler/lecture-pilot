from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from canvas_workspace_fixtures import write_canvas_draft

from test_learning_design_review_routes import _document, _update_payload


def test_learning_map_get_reads_the_approved_published_snapshot_without_rewriting(
    tmp_path: Path,
) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    document = _document().model_copy(
        update={
            "id": "martius-ml-lecture-01",
            "course_id": "martius-ml",
        }
    )
    write_canvas_draft(app.state.canvas_workspace, document)
    client = TestClient(app)
    path = "/admin/courses/martius-ml/lectures/lecture-01/canvas/learning-design"
    review = client.get(path, headers=professor_headers()).json()
    update = _update_payload(review)
    update["objective"] = "Approved objective that is not present in canvas Markdown."
    changed = client.put(path, headers=professor_headers(), json=update)
    assert changed.status_code == 200
    approved = client.post(
        f"{path}/approve",
        headers=professor_headers(),
        json={
            "draft_digest": changed.json()["draft_digest"],
            "source_revision": changed.json()["source_revision"],
            "learning_map_revision": changed.json()["learning_map"]["revision"],
            "report_revision": changed.json()["report"]["report_revision"],
            "acknowledged_warning_ids": [
                item["id"] for item in changed.json()["report"]["diagnostics"]
            ],
        },
    )
    assert approved.status_code == 200
    published = client.post(
        "/admin/courses/martius-ml/lectures/lecture-01/canvas/publish",
        headers=professor_headers(),
    )
    assert published.status_code == 200
    map_path = (
        app.state.canvas_workspace.course_canvas_store.path("martius-ml", "lecture-01")
        / "learning-map.json"
    )
    before = map_path.read_bytes()

    response = client.get(
        "/courses/martius-ml/lectures/lecture-01/learning-map",
        headers=student_headers(),
    )

    assert response.status_code == 200, response.json()
    assert response.json()["objective"] == update["objective"]
    assert map_path.read_bytes() == before
