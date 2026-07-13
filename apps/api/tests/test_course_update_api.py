from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_update_apply import apply_course_update
from lecturepilot.course_update_models import CourseUpdateApplyInput


def test_course_update_detects_unchanged_files_without_creating_work(tmp_path: Path) -> None:
    client = _course_client(tmp_path)
    _upload_live(client, "Lecture01.tex", _lecture("Original"))
    update_id = _create_update(client)
    _upload_update(client, update_id, "Lecture01.tex", _lecture("Original"))

    analysis = client.get(
        f"/admin/courses/update-demo/updates/{update_id}", headers=professor_headers()
    )

    assert analysis.status_code == 200
    assert analysis.json()["unchanged_files"] == 1
    assert analysis.json()["candidates"] == []
    assert analysis.json()["unassigned_files"] == []


def test_course_update_changes_existing_and_appends_new_without_deleting_missing(
    tmp_path: Path,
) -> None:
    client = _course_client(tmp_path)
    _upload_live(client, "Lecture01.tex", _lecture("Original"))
    _upload_live(client, "shared.md", b"# Shared baseline")
    published = _published_file(client, "lecture-01")
    published.parent.mkdir(parents=True)
    published.write_text("published before update", encoding="utf-8")
    update_id = _create_update(client)
    _upload_update(client, update_id, "Lecture01.tex", _lecture("Revised"))
    _upload_update(client, update_id, "Lecture03.tex", _lecture("New topic"))

    analysis = client.get(
        f"/admin/courses/update-demo/updates/{update_id}", headers=professor_headers()
    ).json()
    assert [(item["action"], item["number"]) for item in analysis["candidates"]] == [
        ("update", "01"),
        ("new", "03"),
    ]

    response = client.post(
        f"/admin/courses/update-demo/updates/{update_id}/apply",
        headers=professor_headers(),
        json={
            "lectures": [
                {
                    "lecture_id": "lecture-01",
                    "number": "01",
                    "title": "Existing revised",
                    "date": "2026-05-06",
                    "file_paths": ["Lecture01.tex"],
                },
                {
                    "number": "03",
                    "title": "New topic",
                    "date": "2026-05-20",
                    "file_paths": ["Lecture03.tex"],
                },
            ]
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["affected_lecture_ids"] == ["lecture-01", "lecture-03"]
    uploads = client.app.state.canvas_workspace.layout.course_uploads_dir("update-demo")
    assert (uploads / "Lecture01.tex").read_bytes() == _lecture("Revised")
    assert (uploads / "Lecture03.tex").exists()
    assert (uploads / "shared.md").read_text(encoding="utf-8") == "# Shared baseline"
    assert published.read_text(encoding="utf-8") == "published before update"
    assert [item["id"] for item in response.json()["workspace"]["lectures"]] == [
        "lecture-01",
        "lecture-02",
        "lecture-03",
    ]


def test_unassigned_update_can_be_explicitly_attached_and_reused_for_drafting(
    tmp_path: Path,
) -> None:
    client = _course_client(tmp_path)
    update_id = _create_update(client)
    _upload_update(client, update_id, "examples/new-example.md", b"# Worked example")
    analysis = client.get(
        f"/admin/courses/update-demo/updates/{update_id}", headers=professor_headers()
    ).json()
    assert [item["path"] for item in analysis["unassigned_files"]] == ["examples/new-example.md"]

    response = client.post(
        f"/admin/courses/update-demo/updates/{update_id}/apply",
        headers=professor_headers(),
        json={
            "lectures": [
                {
                    "lecture_id": "lecture-02",
                    "number": "02",
                    "title": "Second",
                    "date": "2026-05-13",
                    "file_paths": ["examples/new-example.md"],
                }
            ]
        },
    )
    assert response.status_code == 200
    manifest = client.app.state.canvas_workspace.layout.lecture_source_manifest_path(
        "update-demo", "lecture-02"
    )
    assert "examples/new-example.md" in manifest.read_text(encoding="utf-8")


def test_course_update_rejects_student_traversal_and_stale_selection(tmp_path: Path) -> None:
    client = _course_client(tmp_path)
    denied = client.post("/admin/courses/update-demo/updates", headers=student_headers())
    assert denied.status_code == 403
    update_id = _create_update(client)
    traversal = client.post(
        f"/admin/courses/update-demo/updates/{update_id}/materials",
        headers=professor_headers(),
        data={"path": "../outside.tex"},
        files={"file": ("outside.tex", _lecture("Unsafe"), "application/x-tex")},
    )
    assert traversal.status_code == 400
    stale = client.post(
        f"/admin/courses/update-demo/updates/{update_id}/apply",
        headers=professor_headers(),
        json={
            "lectures": [
                {
                    "lecture_id": "lecture-01",
                    "number": "01",
                    "title": "First",
                    "date": "2026-05-06",
                    "file_paths": ["not-staged.tex"],
                }
            ]
        },
    )
    assert stale.status_code == 400
    assert not (tmp_path / "outside.tex").exists()


def test_course_update_rolls_back_files_and_schedule_if_metadata_write_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _course_client(tmp_path)
    original = _lecture("Original")
    _upload_live(client, "Lecture01.tex", original)
    update_id = _create_update(client)
    _upload_update(client, update_id, "Lecture01.tex", _lecture("Broken transaction"))
    layout = client.app.state.canvas_workspace.layout
    workspace_path = layout.course_root("update-demo") / "builder" / "course-workspace.json"
    workspace_before = workspace_path.read_bytes()

    def fail_manifest(*args, **kwargs):
        raise OSError("simulated manifest failure")

    monkeypatch.setattr(
        "lecturepilot.course_update_apply.write_lecture_source_manifest", fail_manifest
    )
    payload = CourseUpdateApplyInput.model_validate(
        {
            "lectures": [
                {
                    "lecture_id": "lecture-01",
                    "number": "01",
                    "title": "Should roll back",
                    "date": "2026-05-06",
                    "file_paths": ["Lecture01.tex"],
                }
            ]
        }
    )

    try:
        apply_course_update(layout, "update-demo", update_id, payload)
    except OSError as exc:
        assert "simulated" in str(exc)
    else:
        raise AssertionError("Expected the simulated metadata failure.")

    assert (layout.course_uploads_dir("update-demo") / "Lecture01.tex").read_bytes() == original
    assert workspace_path.read_bytes() == workspace_before
    assert layout.course_update_root("update-demo", update_id).exists()


def _course_client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    client = TestClient(app)
    response = client.post(
        "/admin/course-workspaces",
        headers=professor_headers(),
        json={
            "course_title": "Update Demo",
            "target": "full-course",
            "lectures": [
                {"number": "01", "title": "First", "date": "2026-05-06"},
                {"number": "02", "title": "Second", "date": "2026-05-13"},
            ],
        },
    )
    assert response.status_code == 200
    return client


def _create_update(client: TestClient) -> str:
    response = client.post("/admin/courses/update-demo/updates", headers=professor_headers())
    assert response.status_code == 200
    return response.json()["update_id"]


def _upload_live(client: TestClient, path: str, content: bytes) -> None:
    response = client.post(
        "/admin/courses/update-demo/materials",
        headers=professor_headers(),
        data={"path": path},
        files={"file": (Path(path).name, content, "text/plain")},
    )
    assert response.status_code == 200, response.text


def _upload_update(client: TestClient, update_id: str, path: str, content: bytes) -> None:
    response = client.post(
        f"/admin/courses/update-demo/updates/{update_id}/materials",
        headers=professor_headers(),
        data={"path": path},
        files={"file": (Path(path).name, content, "text/plain")},
    )
    assert response.status_code == 200, response.text


def _published_file(client: TestClient, lecture_id: str) -> Path:
    return (
        client.app.state.canvas_workspace.layout.course_canvas_dir("update-demo", lecture_id)
        / "index.md"
    )


def _lecture(title: str) -> bytes:
    return f"\\documentclass{{beamer}}\n\\title{{{title}}}\n".encode()
