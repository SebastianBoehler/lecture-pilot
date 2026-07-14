from pathlib import Path, PurePosixPath

from fastapi.testclient import TestClient
import pytest

import lecturepilot.secure_upload as secure_upload
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


def test_upload_accepts_legacy_encoded_latex_source(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/admin/courses/martius-ml/materials",
        headers=professor_headers(),
        data={"path": "Lecture02.tex"},
        files={
            "file": (
                "Lecture02.tex",
                b"\\documentclass{beamer}\n% Gr\xfc\xdfe\n",
                "application/x-tex",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["kind"] == "latex"


def test_upload_accepts_latex_style_files(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/admin/courses/martius-ml/materials",
        headers=professor_headers(),
        data={"path": "beamerthemeUniTuebingen.sty"},
        files={
            "file": (
                "beamerthemeUniTuebingen.sty",
                b"\\ProvidesPackage{beamerthemeUniTuebingen}\n",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["kind"] == "latex-support"


def test_upload_rejects_binary_content_disguised_as_latex(tmp_path: Path) -> None:
    client = _client(tmp_path)
    response = client.post(
        "/admin/courses/martius-ml/materials",
        headers=professor_headers(),
        data={"path": "not-really-latex.tex"},
        files={"file": ("not-really-latex.tex", b"\x01" * 128, "application/x-tex")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "File contents do not match the requested file type."


def test_upload_promotion_is_durable_in_target_and_quarantine_directories(
    tmp_path: Path, monkeypatch
) -> None:
    uploads = tmp_path / "uploads"
    quarantine = tmp_path / "quarantine"
    uploads.mkdir()
    quarantine.mkdir()
    source = quarantine / "upload.part"
    source.write_text("source", encoding="utf-8")
    synced: list[Path] = []
    monkeypatch.setattr(secure_upload, "fsync_directory", synced.append)

    target = secure_upload._promote_upload(
        uploads,
        PurePosixPath("Lecture01.tex"),
        source,
    )

    assert target.read_text(encoding="utf-8") == "source"
    assert not source.exists()
    assert synced == [uploads, quarantine]


def test_upload_promotion_crash_never_leaves_two_live_links(tmp_path: Path, monkeypatch) -> None:
    uploads = tmp_path / "uploads"
    quarantine = tmp_path / "quarantine"
    uploads.mkdir()
    quarantine.mkdir()
    source = quarantine / "upload.part"
    source.write_text("source", encoding="utf-8")

    def crash_after_rename(_path: Path) -> None:
        raise SystemExit("simulated process crash")

    monkeypatch.setattr(secure_upload, "fsync_directory", crash_after_rename)

    with pytest.raises(SystemExit, match="simulated process crash"):
        secure_upload._promote_upload(
            uploads,
            PurePosixPath("Lecture01.tex"),
            source,
        )

    target = uploads / "Lecture01.tex"
    assert target.read_text(encoding="utf-8") == "source"
    assert target.stat().st_nlink == 1
    assert not source.exists()


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    return TestClient(app)
