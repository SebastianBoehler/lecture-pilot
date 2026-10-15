from datetime import UTC, datetime
import json

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from canvas_change_test_helpers import (
    CHANGE,
    COURSE,
    LECTURE,
    ScriptedProvider,
    change_headers,
    drafted_client,
)
from authoring_test_helpers import install_author
from lecturepilot.app import create_app
from lecturepilot.canvas.canvas_workspace import CanvasWorkspace
from security_db_helpers import LegacyUniversityAccounts, login, mutation_headers
from test_course_canvas_targeted_repair import _course_client

BODY = {"instruction": "Add a worked example."}


def test_a_lecture_without_draft_or_publication_cannot_be_changed(tmp_path, monkeypatch):
    client = _course_client(tmp_path)
    provider = ScriptedProvider()
    install_author(client, monkeypatch, provider.respond, provider)

    options = client.get(CHANGE, headers=professor_headers())
    posted = client.post(CHANGE, headers=change_headers("change-nothing-0001"), json=BODY)

    for response in (options, posted):
        assert response.status_code == 409, response.text
        assert "Generate a draft first" in response.json()["detail"]
    assert provider.calls == []


def test_unapproved_goals_block_a_change_request(tmp_path) -> None:
    client = _course_client(tmp_path)
    design = client.app.state.canvas_workspace.layout.course_root(COURSE) / "builder"
    for path in design.rglob(f"{LECTURE}*.json"):
        if "practice-design" in str(path):
            path.unlink()

    posted = client.post(CHANGE, headers=change_headers("change-goals-0001"), json=BODY)

    assert posted.status_code == 409, posted.text
    assert "learning goals" in posted.json()["detail"]


def test_a_running_generation_blocks_a_new_change_request(tmp_path, monkeypatch):
    provider = ScriptedProvider()
    client = drafted_client(tmp_path, monkeypatch, provider)
    layout = client.app.state.canvas_workspace.layout
    directory = layout.course_root(COURSE) / "builder" / "generations" / LECTURE
    record = json.loads(next(directory.glob("*.json")).read_text())
    now = datetime.now(UTC).isoformat()
    record.update(status="running", canvas=None, updated_at=now, request_key_hash="9" * 64)
    (directory / f"{'9' * 64}.json").write_text(json.dumps(record))

    posted = client.post(CHANGE, headers=change_headers("change-running-0001"), json=BODY)

    assert posted.status_code == 409, posted.text
    assert "already being generated" in posted.json()["detail"]
    assert provider.calls == []


def test_invalid_instructions_and_unknown_sections_are_rejected(tmp_path, monkeypatch):
    provider = ScriptedProvider()
    client = drafted_client(tmp_path, monkeypatch, provider)

    for index, body in enumerate(
        [
            {"instruction": "   "},
            {"instruction": "x" * 2001},
            {"instruction": "Fix it.", "extra": True},
            {"instruction": "Fix it.", "section_ids": ["learning-unknown"]},
        ]
    ):
        response = client.post(
            CHANGE, headers=change_headers(f"change-invalid-000{index}"), json=body
        )
        assert response.status_code == 422, response.text
    assert provider.calls == []


def test_change_requests_need_a_course_manager_and_an_idempotency_key(tmp_path, monkeypatch):
    client = drafted_client(tmp_path, monkeypatch, ScriptedProvider())

    student = client.post(CHANGE, headers=student_headers(), json=BODY)
    student_options = client.get(CHANGE, headers=student_headers())
    keyless_headers = change_headers("change-keyless-0001")
    del keyless_headers["Idempotency-Key"]
    keyless = client.post(CHANGE, headers=keyless_headers, json=BODY)

    assert student.status_code == 403 and student_options.status_code == 403
    assert keyless.status_code == 400, keyless.text


def test_change_requests_require_course_ownership_and_csrf(tmp_path) -> None:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    app.state.legacy_accounts = LegacyUniversityAccounts(
        {"owner": [], "other": []}, roles_by_user={"owner": "lecturer", "other": "lecturer"}
    )
    owner_client = TestClient(app, base_url="http://localhost:8000")
    owner = login(owner_client, "owner")
    created = owner_client.post(
        "/admin/course-workspaces",
        headers=mutation_headers(owner),
        json={"course_title": "Owned", "lecture_number": "01", "lecture_title": "Mechanism"},
    )
    assert created.status_code == 200, created.text
    path = CHANGE.replace(COURSE, created.json()["course"]["id"])
    other_client = TestClient(app, base_url="http://localhost:8000")
    other = login(other_client, "other")

    no_csrf = owner_client.post(
        path, headers={"Origin": "http://localhost:8000", "Idempotency-Key": "x" * 20}, json=BODY
    )
    denied = other_client.post(
        path, headers={**mutation_headers(other), "Idempotency-Key": "x" * 20}, json=BODY
    )
    denied_options = other_client.get(path)

    assert no_csrf.status_code == 403, no_csrf.text
    for response in (denied, denied_options):
        assert response.status_code == 403, response.text
        assert response.json()["detail"] == "Course ownership is required."
