from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_upload_rejects_mime_mismatch_without_publishing_partial_file(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/admin/courses/martius-ml/materials",
        headers=professor_headers(),
        data={"path": "images/fake.png"},
        files={"file": ("fake.png", b"not an image", "image/png")},
    )

    uploads = client.app.state.canvas_workspace.layout.course_uploads_dir("martius-ml")
    assert response.status_code == 400
    assert not (uploads / "images" / "fake.png").exists()
    assert not list((uploads / ".quarantine").glob("*.part"))


def test_upload_rejects_symlink_parent_and_preserves_outside_file(tmp_path: Path) -> None:
    client = _client(tmp_path)
    uploads = client.app.state.canvas_workspace.layout.course_uploads_dir("martius-ml")
    outside = tmp_path / "outside"
    uploads.mkdir(parents=True)
    outside.mkdir()
    protected = outside / "notes.md"
    protected.write_text("protected", encoding="utf-8")
    (uploads / "linked").symlink_to(outside, target_is_directory=True)

    response = client.post(
        "/admin/courses/martius-ml/materials",
        headers=professor_headers(),
        data={"path": "linked/notes.md"},
        files={"file": ("notes.md", b"changed", "text/markdown")},
    )

    assert response.status_code == 400
    assert protected.read_text(encoding="utf-8") == "protected"


def test_upload_rejects_active_svg_content(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/admin/courses/martius-ml/materials",
        headers=professor_headers(),
        data={"path": "images/active.svg"},
        files={
            "file": (
                "active.svg",
                b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
                "image/svg+xml",
            )
        },
    )
    assert response.status_code == 400


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    return TestClient(app)
