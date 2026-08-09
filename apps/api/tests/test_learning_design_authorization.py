import json
from pathlib import Path

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from security_db_helpers import FakeUniversityAdapter, login, mutation_headers

from test_learning_design_review_routes import _document, _update_payload


def test_learning_design_review_is_private_to_the_owner_professor(tmp_path: Path) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    app.state.tuebingen_adapter = FakeUniversityAdapter({"owner": [], "other": []})
    owner_client = TestClient(app, base_url="http://localhost:8000")
    app.state.tuebingen_adapter.roles_by_user["owner"] = "lecturer"
    owner = login(owner_client, "owner")
    created = owner_client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(owner),
        json={
            "course_title": "Private Learning Design",
            "target": "single-lecture",
            "lecture_number": "01",
            "lecture_title": "Mechanism",
        },
    )
    assert created.status_code == 200
    course_id = created.json()["course"]["id"]
    manifest = app.state.canvas_workspace.layout.lecture_source_manifest_path(
        course_id, "lecture-01"
    )
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "course_id": course_id,
                "lecture_id": "lecture-01",
                "files": [{"path": "lecture.md", "sha256": "a" * 64}],
            }
        ),
        encoding="utf-8",
    )
    app.state.canvas_workspace.write_course_canvas_draft(
        _document().model_copy(update={"course_id": course_id, "id": f"{course_id}-lecture-01"})
    )
    owner_review = owner_client.get(
        f"/admin/courses/{course_id}/lectures/lecture-01/canvas/learning-design"
    )
    assert owner_review.status_code == 200

    other_client = TestClient(app, base_url="http://localhost:8000")
    app.state.tuebingen_adapter.roles_by_user["other"] = "lecturer"
    other = login(other_client, "other")
    path = f"/admin/courses/{course_id}/lectures/lecture-01/canvas/learning-design"
    denied_get = other_client.get(path)
    denied_update = other_client.put(
        path,
        headers=mutation_headers(other),
        json=_update_payload(owner_review.json()),
    )
    denied_approval = other_client.post(
        f"{path}/approve",
        headers=mutation_headers(other),
        json={
            "draft_digest": owner_review.json()["draft_digest"],
            "source_revision": owner_review.json()["source_revision"],
            "learning_map_revision": owner_review.json()["learning_map"]["revision"],
        },
    )

    for denied in (denied_get, denied_update, denied_approval):
        assert denied.status_code == 403
        assert denied.json()["detail"] == "Course ownership is required."
