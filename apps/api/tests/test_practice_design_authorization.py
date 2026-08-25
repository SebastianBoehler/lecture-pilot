from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from practice_design_test_helpers import proposal
from security_db_helpers import FakeUniversityAdapter, login, mutation_headers


def test_practice_design_routes_are_private_to_the_owner_professor(tmp_path) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    app.state.tuebingen_adapter = FakeUniversityAdapter({"owner": [], "other": []})
    owner_client = TestClient(app, base_url="http://localhost:8000")
    app.state.tuebingen_adapter.roles_by_user["owner"] = "lecturer"
    owner = login(owner_client, "owner")
    created = owner_client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(owner),
        json={
            "course_title": "Private Practice Design",
            "target": "single-lecture",
            "lecture_number": "01",
            "lecture_title": "Mechanism",
        },
    )
    assert created.status_code == 200
    course_id = created.json()["course"]["id"]
    other_client = TestClient(app, base_url="http://localhost:8000")
    app.state.tuebingen_adapter.roles_by_user["other"] = "lecturer"
    other = login(other_client, "other")
    path = f"/admin/courses/{course_id}/lectures/lecture-01/practice-design"
    plan = proposal().model_dump(mode="json")
    update = {
        "source_revision": "a" * 64,
        "practice_design_revision": "b" * 64,
        **plan,
    }

    denied = (
        other_client.get(path),
        other_client.post(f"{path}/proposal", headers=mutation_headers(other)),
        other_client.put(path, headers=mutation_headers(other), json=update),
        other_client.post(
            f"{path}/approve",
            headers=mutation_headers(other),
            json={"source_revision": "a" * 64, "practice_design_revision": "b" * 64},
        ),
    )

    for response in denied:
        assert response.status_code == 403
        assert response.json()["detail"] == "Course ownership is required."
