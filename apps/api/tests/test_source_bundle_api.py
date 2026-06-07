from pathlib import Path

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_source_bundle_endpoint_lists_professor_materials(tmp_path: Path) -> None:
    material_root = tmp_path / "course"
    _write(material_root / "Lecture03-eng.tex")
    _write(material_root / "images" / "Ch3" / "diagram.pdf")
    _write(material_root / "videos" / "demo.mp4")
    _write(material_root / "code" / "notebook.ipynb")
    _write(material_root / ".lecturepilot-previews" / "diagram.png")

    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )
    client = TestClient(app)

    response = client.get("/courses/martius-ml/source-bundle")

    assert response.status_code == 200
    payload = response.json()
    assert payload["counts_by_kind"] == {
        "latex": 1,
        "notebook": 1,
        "pdf": 1,
        "video": 1,
    }
    assert [item["path"] for item in payload["files"]] == [
        "Lecture03-eng.tex",
        "code/notebook.ipynb",
        "images/Ch3/diagram.pdf",
        "videos/demo.mp4",
    ]
    upload_types = {item["suffix"]: item for item in payload["supported_uploads"]}
    assert upload_types[".tex"]["kind"] == "latex"
    assert upload_types[".mp4"]["max_bytes"] == 500 * 1024 * 1024


def test_professor_uploads_course_materials_into_source_bundle(tmp_path: Path) -> None:
    client, material_root = _client(tmp_path)

    for path, content in (
        ("Lecture03-eng.tex", _latex_source()),
        ("notes/overview.md", b"# Notes\n"),
        ("slides/lecture.pdf", b"%PDF-1.4\n"),
        ("images/plot.png", b"\x89PNG\r\n"),
        ("videos/demo.mp4", b"\x00\x00\x00\x18ftypmp42"),
    ):
        response = client.post(
            "/admin/courses/martius-ml/materials",
            data={"path": path},
            files={"file": (Path(path).name, content)},
            headers=_professor_headers(),
        )

        assert response.status_code == 200
        assert (material_root / path).exists()

    payload = client.get("/courses/martius-ml/source-bundle").json()
    assert payload["counts_by_kind"] == {
        "image": 1,
        "latex": 1,
        "markdown": 1,
        "pdf": 1,
        "video": 1,
    }


def test_student_cannot_upload_course_material(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.post(
        "/admin/courses/martius-ml/materials",
        data={"path": "Lecture03-eng.tex"},
        files={"file": ("Lecture03-eng.tex", _latex_source())},
        headers={**_professor_headers(), "X-User-Role": "student"},
    )

    assert response.status_code == 403


def test_course_material_upload_rejects_unsafe_paths(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.post(
        "/admin/courses/martius-ml/materials",
        data={"path": "../Lecture03-eng.tex"},
        files={"file": ("Lecture03-eng.tex", _latex_source())},
        headers=_professor_headers(),
    )

    assert response.status_code == 400


def test_uploaded_latex_can_seed_a_canvas_document(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    client.post(
        "/admin/courses/martius-ml/materials",
        data={"path": "Lecture03-eng.tex"},
        files={"file": ("Lecture03-eng.tex", _latex_source())},
        headers=_professor_headers(),
    )

    response = client.get("/courses/martius-ml/lectures/lecture-03/canvas?user_id=student01")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_ref"] == "Lecture03-eng.tex"
    assert [section["title"] for section in payload["sections"]] == [
        "Uploaded Bayes Concept",
        "Risk Check",
    ]
    list_blocks = [block for block in payload["sections"][0]["blocks"] if block["type"] == "list"]
    assert list_blocks[0]["items"] == [
        "Prior belief before seeing evidence",
        "Likelihood of evidence under each class",
        "Posterior decision after applying Bayes rule",
    ]


def _client(tmp_path: Path) -> tuple[TestClient, Path]:
    material_root = tmp_path / "course"
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )
    return TestClient(app), material_root


def _professor_headers() -> dict[str, str]:
    return {
        "X-Tenant-Id": "tenant-tuebingen",
        "X-User-Id": "prof01",
        "X-User-Role": "professor",
    }


def _latex_source() -> bytes:
    return br"""
\title{Uploaded Lecture}
\begin{frame}{Uploaded Bayes Concept}
\begin{itemize}
\item Prior belief before seeing evidence
\item Likelihood of evidence under each class
\item Posterior decision after applying Bayes rule
\end{itemize}
\[
P(C\mid X)=\frac{P(X\mid C)P(C)}{P(X)}
\]
\end{frame}
\begin{frame}{Risk Check}
Expected risk changes the decision threshold.
\end{frame}
"""


def _write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("demo", encoding="utf-8")
