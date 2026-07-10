from pathlib import Path

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from auth_helpers import professor_headers, student_headers


def test_source_bundle_endpoint_lists_only_uploaded_materials(tmp_path: Path) -> None:
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

    response = client.get("/courses/martius-ml/source-bundle", headers=professor_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["counts_by_kind"] == {}
    assert payload["files"] == []
    upload_types = {item["suffix"]: item for item in payload["supported_uploads"]}
    assert upload_types[".tex"]["kind"] == "latex"
    assert upload_types[".mp4"]["max_bytes"] == 500 * 1024 * 1024


def test_professor_uploads_course_materials_into_source_bundle(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    for path, content in (
        ("Lecture03-eng.tex", _latex_source()),
        ("notes/overview.md", b"# Notes\n"),
        ("slides/lecture.pdf", b"%PDF-1.4\n"),
        ("images/plot.png", b"\x89PNG\r\n\x1a\n"),
        ("videos/demo.mp4", b"\x00\x00\x00\x18ftypmp42"),
    ):
        response = client.post(
            "/admin/courses/martius-ml/materials",
            data={"path": path},
            files={"file": (Path(path).name, content)},
            headers=_professor_headers(),
        )

        assert response.status_code == 200
        upload_path = client.app.state.canvas_workspace.course_upload_path(
            course_id="martius-ml",
            path=path,
        )
        assert upload_path.exists()
        assert "storage_path" not in response.json()

    payload = client.get("/courses/martius-ml/source-bundle", headers=professor_headers()).json()
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


def test_student_cannot_scan_source_bundle(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.get("/courses/martius-ml/source-bundle", headers=student_headers("student01"))

    assert response.status_code == 403


def test_source_bundle_requires_authenticated_headers(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)

    response = client.get("/courses/martius-ml/source-bundle")

    assert response.status_code == 401


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
    workspace = client.app.state.canvas_workspace
    source = workspace.source_document(
        course_id="martius-ml",
        lecture_id="lecture-03",
        workspace_path="published/index.md",
    )
    workspace.write_course_canvas(source)

    response = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas?user_id=student01",
        headers=student_headers("student01"),
    )

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


def test_nested_uploaded_latex_matches_requested_lecture_before_sorted_fallback(tmp_path: Path) -> None:
    client, _ = _client(tmp_path)
    for path, title in (
        ("uploads/course/Lecture01-eng.tex", "Wrong Overview"),
        ("uploads/course/Lecture03-eng.tex", "Correct Bayes"),
    ):
        client.post(
            "/admin/courses/martius-ml/materials",
            data={"path": path},
            files={"file": (Path(path).name, _latex_source_with_title(title))},
            headers=_professor_headers(),
        )

    source = client.app.state.canvas_workspace.source_document(
        course_id="martius-ml",
        lecture_id="lecture-03",
        workspace_path="published/index.md",
    )

    assert source.source_ref == "Lecture03-eng.tex"
    assert source.sections[0].title == "Correct Bayes"


def test_professor_canvas_draft_stays_private_until_publish(tmp_path: Path) -> None:
    client, material_root = _client(tmp_path)
    client.app.state.course_planner = _FakeCoursePlanner()
    store = client.app.state.canvas_workspace.course_canvas_store
    draft_dir = store.draft_path("martius-ml", "lecture-03")
    canvas_dir = store.path("martius-ml", "lecture-03")
    stale = draft_dir / "sections" / "99-stale.md"
    _write(stale)
    client.post(
        "/admin/courses/martius-ml/materials",
        data={"path": "Lecture03-eng.tex"},
        files={"file": ("Lecture03-eng.tex", _latex_source())},
        headers=_professor_headers(),
    )

    draft = client.post(
        "/admin/courses/martius-ml/lectures/lecture-03/canvas/draft",
        headers=_professor_headers(),
    )

    assert draft.status_code == 200
    assert draft.json()["source_kind"] == "generated"
    assert (draft_dir / "index.md").exists()
    assert not (canvas_dir / "index.md").exists()
    assert not stale.exists()

    student = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas?user_id=student01",
        headers=student_headers("student01"),
    )
    assert student.status_code == 404

    publish = client.post(
        "/admin/courses/martius-ml/lectures/lecture-03/canvas/publish",
        headers=_professor_headers(),
    )

    assert publish.status_code == 200
    assert publish.json()["published"] is True
    assert "published_by" not in publish.json()
    assert (canvas_dir / "index.md").exists()

    student = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas?user_id=student01",
        headers=student_headers("student01"),
    )

    assert student.status_code == 200
    payload = student.json()
    assert payload["source_kind"] == "generated"
    assert [section["title"] for section in payload["sections"]] == ["Planner summary"]
    assert payload["sections"][0]["blocks"][0]["text"] == "Bayes rule becomes a compact learning section."


def _client(tmp_path: Path) -> tuple[TestClient, Path]:
    material_root = tmp_path / "course"
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )
    return TestClient(app), material_root


def _professor_headers() -> dict[str, str]:
    return professor_headers()


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


def _latex_source_with_title(title: str) -> bytes:
    return rf"""
\title{{Uploaded Lecture}}
\begin{{frame}}{{{title}}}
Bayes turns evidence into a posterior decision.
\end{{frame}}
""".encode()


def _write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("demo", encoding="utf-8")


class _FakeCoursePlanner:
    async def plan_canvas(self, source_document):
        assert source_document.source_ref == "Lecture03-eng.tex"
        return source_document.model_copy(
            update={
                "source_kind": "generated",
                "source_ref": "course planner from Lecture03-eng.tex",
                "sections": [
                    CanvasSection(
                        id="planner-summary",
                        title="Planner summary",
                        source_ref="Lecture03-eng.tex frame 1",
                        blocks=[
                            CanvasBlock(
                                id="planner-summary-p-1",
                                type="paragraph",
                                text="Bayes rule becomes a compact learning section.",
                            )
                        ],
                    )
                ],
            }
        )
