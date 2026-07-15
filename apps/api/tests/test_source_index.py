from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers
import lecturepilot.course_routes as course_routes
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.source_index_models import CourseSourceIndex


def test_upload_updates_hash_addressed_course_source_index(tmp_path: Path) -> None:
    client = _client(tmp_path)
    content = b"# Indexed lecture\n\nThis source has stable teaching evidence."

    response = client.post(
        "/admin/courses/indexed-course/materials",
        data={"path": "Lecture01/notes.md"},
        files={"file": ("notes.md", content)},
        headers=professor_headers(),
    )

    assert response.status_code == 200
    index_path = client.app.state.canvas_workspace.layout.course_source_index_path("indexed-course")
    index = CourseSourceIndex.model_validate_json(index_path.read_text(encoding="utf-8"))
    assert index.course_id == "indexed-course"
    assert len(index.files) == 1
    assert index.files[0].path == "Lecture01/notes.md"
    assert index.files[0].sha256 == hashlib.sha256(content).hexdigest()
    assert index.files[0].status == "indexed"


def test_deferred_upload_batch_refreshes_source_index_once(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path)
    refreshes = 0
    audit_events: list[dict] = []
    original_index = course_routes.indexed_course_files

    def counted_index(*args, **kwargs):
        nonlocal refreshes
        refreshes += 1
        return original_index(*args, **kwargs)

    monkeypatch.setattr(course_routes, "indexed_course_files", counted_index)
    monkeypatch.setattr(
        course_routes,
        "record_audit_event",
        lambda *args, **kwargs: audit_events.append(kwargs),
    )

    for number in range(6):
        response = client.post(
            "/admin/courses/indexed-course/materials",
            data={
                "path": f"Lecture{number:02d}/notes.md",
                "refresh_index": "false",
            },
            files={"file": ("notes.md", f"# Lecture {number}".encode())},
            headers=professor_headers(),
        )
        assert response.status_code == 200

    index_path = client.app.state.canvas_workspace.layout.course_source_index_path("indexed-course")
    assert refreshes == 0
    assert not index_path.exists()
    assert [event["event_type"] for event in audit_events] == ["course.material_uploaded"] * 6

    manifest = client.get("/courses/indexed-course/source-bundle", headers=professor_headers())

    assert manifest.status_code == 200
    assert len(manifest.json()["files"]) == 6
    assert refreshes == 1
    assert index_path.exists()


def test_oversized_streamed_upload_leaves_no_partial_file(tmp_path: Path) -> None:
    client = _client(tmp_path)
    content = b"x" * (2 * 1024 * 1024 + 1)

    response = client.post(
        "/admin/courses/indexed-course/materials",
        data={"path": "Lecture01/too-large.txt"},
        files={"file": ("too-large.txt", content)},
        headers=professor_headers(),
    )

    assert response.status_code == 400
    target = client.app.state.canvas_workspace.course_upload_path(
        course_id="indexed-course", path="Lecture01/too-large.txt"
    )
    assert not target.exists()
    assert not list(target.parent.glob(".upload-*"))


def test_rejected_replacement_preserves_the_existing_material(tmp_path: Path) -> None:
    client = _client(tmp_path)
    target = client.app.state.canvas_workspace.course_upload_path(
        course_id="indexed-course", path="Lecture01/notes.txt"
    )
    target.parent.mkdir(parents=True)
    target.write_bytes(b"existing lecture material")

    response = client.post(
        "/admin/courses/indexed-course/materials",
        data={"path": "Lecture01/notes.txt"},
        files={"file": ("notes.txt", b"x" * (2 * 1024 * 1024 + 1))},
        headers=professor_headers(),
    )

    assert response.status_code == 400
    assert target.read_bytes() == b"existing lecture material"
    assert not list(target.parent.glob(".upload-*"))


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    return TestClient(app)
