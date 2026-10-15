from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas.canvas_workspace import CanvasWorkspace
from lecturepilot.learning_design.course_learning_intent import goal_for
from practice_design_test_helpers import proposal
from security_db_helpers import LegacyUniversityAccounts, login, mutation_headers


def test_practice_design_routes_are_private_to_the_owner_professor(tmp_path) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    app.state.legacy_accounts = LegacyUniversityAccounts({"owner": [], "other": []})
    owner_client = TestClient(app, base_url="http://localhost:8000")
    app.state.legacy_accounts.roles_by_user["owner"] = "lecturer"
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
    app.state.legacy_accounts.roles_by_user["other"] = "lecturer"
    other = login(other_client, "other")
    path = f"/admin/courses/{course_id}/lectures/lecture-01/practice-design"
    revisions = {"source_revision": "a" * 64, "practice_design_revision": "b" * 64}
    plan = proposal()
    goals = {
        "lecture_title": plan.lecture_title,
        "objective": plan.objective,
        "planning_context": plan.planning_context.model_dump(mode="json"),
        "goals": [goal_for(target).model_dump(mode="json") for target in plan.targets],
    }

    denied = (
        other_client.get(path),
        other_client.get(f"{path}/readiness"),
        other_client.get(f"{path}/intent/findings"),
        other_client.post(f"{path}/intent/proposal", headers=mutation_headers(other)),
        other_client.put(
            f"{path}/intent", headers=mutation_headers(other), json={**revisions, **goals}
        ),
        other_client.post(
            f"{path}/intent/approve", headers=mutation_headers(other), json=revisions
        ),
    )

    for response in denied:
        assert response.status_code == 403
        assert response.json()["detail"] == "Course ownership is required."
