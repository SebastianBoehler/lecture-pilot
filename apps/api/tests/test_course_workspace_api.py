from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.models import LectureScheduleItem, LectureScheduleProposal


def test_professor_creates_stable_course_workspace_ids(tmp_path: Path) -> None:
    client = _client(tmp_path)

    first = _create_workspace(client, "Demo ML Course", "03", "Bayesian Decision Theory")
    second = _create_workspace(client, "Robotics Seminar", "7", "Policy Gradients")
    seeded = _create_workspace(client, "Grundlagen des Maschinellen Lernens", "03", "Bayesian Decision Theory")

    assert first["course"]["id"] == "demo-ml-course"
    assert first["active_lecture_id"] == "lecture-03"
    assert first["lectures"][0]["course_id"] == "demo-ml-course"
    assert second["course"]["id"] == "robotics-seminar"
    assert second["active_lecture_id"] == "lecture-07"
    assert second["lectures"][0]["course_id"] == "robotics-seminar"
    assert seeded["course"]["id"] == "martius-ml"
    assert seeded["lectures"][0]["course_id"] == "martius-ml"


def test_full_course_workspace_accepts_dated_lecture_schedule(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Demo ML Course",
            "target": "full-course",
            "lectures": [
                {
                    "number": "01",
                    "title": "Course Setup",
                    "date": "2026-05-06",
                    "material_path": "Lecture01.tex",
                },
                {
                    "number": "02",
                    "title": "Bayesian Decision Theory",
                    "date": "2026-05-13",
                    "material_path": "Lecture02.tex",
                },
            ],
        },
        headers=professor_headers("prof-demo"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_lecture_id"] == "lecture-01"
    assert [lecture["date"] for lecture in payload["lectures"]] == ["2026-05-06", "2026-05-13"]
    assert payload["lectures"][1]["material_path"] == "Lecture02.tex"


def test_professor_can_infer_full_course_schedule_from_bundle(tmp_path: Path) -> None:
    client = _client(tmp_path)
    planner = _FakeLectureSchedulePlanner()
    client.app.state.lecture_schedule_planner = planner
    _create_workspace(client, "Demo ML Course", "01", "Course Setup")
    for path, content in [
        ("uploads/Lecture01-eng.tex", br"\begin{frame}{Course Setup}Intro\end{frame}"),
        ("uploads/Lecture02_old.tex", br"\begin{frame}{Old Version}Ignore\end{frame}"),
        ("uploads/Lecture02-eng.tex", br"\begin{frame}{Bayes Classifier}Bayes\end{frame}"),
    ]:
        response = client.post(
            "/admin/courses/demo-ml-course/materials",
            data={"path": path},
            files={"file": (Path(path).name, content)},
            headers=professor_headers(),
        )
        assert response.status_code == 200

    response = client.get(
        "/admin/courses/demo-ml-course/lecture-schedule"
        "?first_lecture_date=2026-05-06",
        headers=professor_headers(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert [lecture["number"] for lecture in payload["lectures"]] == ["01", "02"]
    assert [lecture["date"] for lecture in payload["lectures"]] == ["2026-05-06", "2026-05-13"]
    assert payload["lectures"][1]["title"] == "Agentic Bayes and Validation"
    assert payload["lectures"][1]["material_path"] == "uploads/Lecture02-eng.tex"
    assert planner.last_requested_count is None
    assert planner.last_first_lecture_date == "2026-05-06"
    assert "uploads/Lecture01-eng.tex" in planner.last_paths


def test_schedule_inference_rejects_invalid_start_date(tmp_path: Path) -> None:
    client = _client(tmp_path)
    _create_workspace(client, "Demo ML Course", "01", "Course Setup")

    response = client.get(
        "/admin/courses/demo-ml-course/lecture-schedule?first_lecture_date=tomorrow",
        headers=professor_headers(),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid first lecture date."


def test_dynamic_course_workspace_uses_uploaded_source(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.course_planner = _FakeCoursePlanner()
    _create_workspace(client, "Demo ML Course", "07", "Kernel Methods")

    upload = client.post(
        "/admin/courses/demo-ml-course/materials",
        data={"path": "uploads/Lecture07.tex"},
        files={"file": ("Lecture07.tex", _latex_source())},
        headers=professor_headers(),
    )
    assert upload.status_code == 200

    bundle = client.get("/courses/demo-ml-course/source-bundle", headers=professor_headers())
    assert bundle.status_code == 200
    assert [item["path"] for item in bundle.json()["files"]] == ["uploads/Lecture07.tex"]

    draft = client.post(
        "/admin/courses/demo-ml-course/lectures/lecture-07/canvas/draft",
        headers=professor_headers(),
    )
    assert draft.status_code == 200
    assert draft.json()["course_id"] == "demo-ml-course"
    assert draft.json()["lecture_id"] == "lecture-07"
    assert draft.json()["source_kind"] == "generated"
    assert "/canvas-drafts/" in draft.json()["workspace_path"]

    student = client.get(
        "/courses/demo-ml-course/lectures/lecture-07/canvas?user_id=student01",
        headers=student_headers("student01"),
    )
    assert student.status_code == 404

    publish = client.post(
        "/admin/courses/demo-ml-course/lectures/lecture-07/canvas/publish",
        headers=professor_headers(),
    )
    assert publish.status_code == 200
    assert publish.json()["published"] is True
    assert publish.json()["version"] == 1
    assert publish.json()["published_at"]

    status = client.get(
        "/courses/demo-ml-course/lectures/lecture-07/canvas/publication",
        headers=student_headers("student01"),
    )
    assert status.status_code == 200
    assert status.json()["published"] is True

    student = client.get(
        "/courses/demo-ml-course/lectures/lecture-07/canvas?user_id=student01",
        headers=student_headers("student01"),
    )
    assert student.status_code == 200
    assert student.json()["sections"][0]["title"] == "Planner summary"


def test_course_canvas_draft_can_use_markdown_text_and_pdf_without_latex(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.course_planner = _FakeMixedSourcePlanner()
    _create_workspace(client, "Mixed Source Course", "01", "Evidence and Risk")

    uploads = [
        ("notes/overview.md", b"# Evidence Update\n\nBayes combines prior belief with likelihood evidence."),
        ("notes/risk.txt", b"Risk-sensitive classification changes decisions when errors have different costs."),
        ("slides/risk.pdf", _pdf_source("PDF slide text explains posterior risk and reject decisions.")),
        ("figures/risk.png", b"\x89PNG\r\n"),
        ("figures/risk.png.json", b'{"title":"Risk regions","description":"Posterior and loss threshold graphic"}'),
        ("videos/decision.mp4", b"\x00\x00\x00\x18ftypmp42"),
        ("videos/decision.json", b'{"title":"Decision walkthrough","description":"Professor-provided media"}'),
    ]
    for path, content in uploads:
        response = client.post(
            "/admin/courses/mixed-source-course/materials",
            data={"path": path},
            files={"file": (Path(path).name, content)},
            headers=professor_headers(),
        )
        assert response.status_code == 200

    draft = client.post(
        "/admin/courses/mixed-source-course/lectures/lecture-01/canvas/draft",
        headers=professor_headers(),
    )

    assert draft.status_code == 200
    assert draft.json()["source_kind"] == "generated"
    assert draft.json()["source_ref"] == "course planner from notes/overview.md, notes/risk.txt, slides/risk.pdf"

    asset = client.get("/course-assets/mixed-source-course/lecture-01/figures/risk.png")
    assert asset.status_code == 200
    assert asset.content.startswith(b"\x89PNG")
    video = client.get("/course-assets/mixed-source-course/lecture-01/videos/decision.mp4")
    assert video.status_code == 200
    assert video.content.startswith(b"\x00\x00\x00\x18ftyp")


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    return TestClient(app)


def _create_workspace(
    client: TestClient,
    course_title: str,
    lecture_number: str,
    lecture_title: str,
) -> dict:
    response = client.post(
        "/admin/course-workspaces",
        json={
            "course_title": course_title,
            "lecture_number": lecture_number,
            "lecture_title": lecture_title,
            "target": "single-lecture",
        },
        headers=professor_headers("prof-demo"),
    )
    assert response.status_code == 200
    return response.json()


def _latex_source() -> bytes:
    return br"""
\title{Uploaded Lecture}
\begin{frame}{Uploaded Concept}
Bayes turns evidence into a posterior decision.
\[
P(C\mid X)=\frac{P(X\mid C)P(C)}{P(X)}
\]
\end{frame}
"""


def _pdf_source(text: str) -> bytes:
    import fitz

    document = fitz.open()
    page = document.new_page(width=320, height=160)
    page.insert_text((24, 72), text)
    payload = document.tobytes()
    document.close()
    return payload


class _FakeCoursePlanner:
    async def plan_canvas(self, source_document):
        assert source_document.course_id == "demo-ml-course"
        assert source_document.lecture_id == "lecture-07"
        assert source_document.source_ref == "uploads/Lecture07.tex"
        assert source_document.source_kind == "markdown"
        return source_document.model_copy(
            update={
                "source_kind": "generated",
                "source_ref": "course planner from uploads/Lecture07.tex",
                "sections": [
                    CanvasSection(
                        id="planner-summary",
                        title="Planner summary",
                        source_ref="uploads/Lecture07.tex frame 1",
                        blocks=[
                            CanvasBlock(
                                id="planner-summary-p-1",
                                type="paragraph",
                                text="The uploaded dynamic course source seeded this canvas.",
                            )
                        ],
                    )
                ],
            }
        )


class _FakeLectureSchedulePlanner:
    def __init__(self) -> None:
        self.last_first_lecture_date = None
        self.last_paths: list[str] = []
        self.last_requested_count = None

    async def propose_schedule(self, *, course_id, files, roots, first_lecture_date, requested_count):
        self.last_first_lecture_date = first_lecture_date.isoformat()
        self.last_paths = [item.path for item in files]
        self.last_requested_count = requested_count
        return LectureScheduleProposal(
            course_id=course_id,
            source_paths=["uploads/Lecture01-eng.tex", "uploads/Lecture02-eng.tex"],
            lectures=[
                LectureScheduleItem(
                    number="01",
                    title="Agentic Course Setup",
                    date="2026-05-06",
                    material_path="uploads/Lecture01-eng.tex",
                ),
                LectureScheduleItem(
                    number="02",
                    title="Agentic Bayes and Validation",
                    date="2026-05-13",
                    material_path="uploads/Lecture02-eng.tex",
                ),
            ],
        )


class _FakeMixedSourcePlanner:
    async def plan_canvas(self, source_document):
        evidence = "\n".join(
            block.text or ""
            for section in source_document.sections
            for block in section.blocks
        )
        assert source_document.source_kind == "markdown"
        assert "Bayes combines prior belief" in evidence
        assert "different costs" in evidence
        assert "posterior risk" in evidence
        assert any(
            block.type == "asset" and block.asset_path == "slides/risk.pdf"
            for section in source_document.sections
            for block in section.blocks
        )
        assert any(
            block.type == "asset" and block.caption.startswith("Risk regions")
            for section in source_document.sections
            for block in section.blocks
        )
        assert any(
            block.type == "video" and block.asset_path == "videos/decision.mp4"
            for section in source_document.sections
            for block in section.blocks
        )
        return source_document.model_copy(
            update={
                "source_kind": "generated",
                "source_ref": f"course planner from {source_document.source_ref}",
                "sections": [
                    CanvasSection(
                        id="mixed-source-summary",
                        title="Mixed source summary",
                        source_ref=source_document.source_ref,
                        blocks=[
                            CanvasBlock(
                                id="mixed-source-summary-p-1",
                                type="paragraph",
                                text="The planner saw Markdown, text, and PDF evidence.",
                            )
                        ],
                    )
                ],
            }
        )
