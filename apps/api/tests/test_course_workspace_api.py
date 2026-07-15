import json
import logging
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import pending_university_login, professor_headers, student_headers
from canvas_workspace_fixtures import published_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.logging_observability import LOGGER_NAME, LoggingObservability
from lecturepilot.models import LectureScheduleItem, LectureScheduleProposal
from lecturepilot.university_models import ExternalCourseCandidate, UniversityLoginResult


def test_professor_creates_stable_course_workspace_ids(tmp_path: Path) -> None:
    client = _client(tmp_path)

    first = _create_workspace(client, "Demo ML Course", "03", "Bayesian Decision Theory")
    second = _create_workspace(client, "Robotics Seminar", "7", "Policy Gradients")
    seeded = _create_workspace(
        client, "Grundlagen des Maschinellen Lernens", "03", "Bayesian Decision Theory"
    )

    assert first["course"]["id"] == "demo-ml-course"
    assert first["course"]["access_policy"] == "tuebingen_enrolled"
    assert first["active_lecture_id"] == "lecture-03"
    assert first["lectures"][0]["course_id"] == "demo-ml-course"
    assert second["course"]["id"] == "robotics-seminar"
    assert second["active_lecture_id"] == "lecture-07"
    assert second["lectures"][0]["course_id"] == "robotics-seminar"
    assert seeded["course"]["id"] == "martius-ml"
    assert seeded["lectures"][0]["course_id"] == "martius-ml"


def test_professor_sets_public_course_workspace_visibility(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/admin/course-workspaces",
        json={
            "access_policy": "public",
            "course_title": "Public ML Course",
            "lecture_number": "01",
            "lecture_title": "Open Lecture",
        },
        headers=professor_headers("prof-demo"),
    )

    assert response.status_code == 200
    assert response.json()["course"]["access_policy"] == "public"


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


def test_created_course_workspace_persists_lecture_schedule(tmp_path: Path) -> None:
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
    for lecture_id in ("lecture-01", "lecture-02"):
        client.app.state.canvas_workspace.write_course_canvas(
            published_course_canvas("demo-ml-course", lecture_id)
        )

    lectures = client.get("/courses/demo-ml-course/lectures", headers=student_headers("student01"))

    assert lectures.status_code == 200
    payload = lectures.json()
    assert [item["lecture"]["id"] for item in payload] == ["lecture-01", "lecture-02"]
    assert payload[1]["lecture"]["material_path"] == "Lecture02.tex"


def test_live_login_does_not_grant_courses_from_demo_flag(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("LECTUREPILOT_DEMO_INCLUDE_CREATED_COURSES", raising=False)
    client = _client(tmp_path)
    client.app.state.tuebingen_adapter = _FakeLoginAdapter()
    _create_workspace(client, "Grundlagen des Maschinellen Lernens", "01", "Introduction")

    response = client.post(
        "/auth/login",
        json={"username": "student01", "password": "secret", "term": "Sommer 2026"},
    )

    assert response.status_code == 200
    assert _course_titles(response.json()) == []

    monkeypatch.setenv("LECTUREPILOT_DEMO_INCLUDE_CREATED_COURSES", "true")
    response = client.post(
        "/auth/login",
        json={"username": "student01", "password": "secret", "term": "Sommer 2026"},
    )

    assert response.status_code == 200
    assert _course_titles(response.json()) == []


def test_professor_can_infer_full_course_schedule_from_bundle(tmp_path: Path, caplog) -> None:
    client = _client(tmp_path)
    planner = _FakeLectureSchedulePlanner()
    client.app.state.lecture_schedule_planner = planner
    client.app.state.observability = LoggingObservability()
    _create_workspace(client, "Demo ML Course", "01", "Course Setup")
    for path, content in [
        ("uploads/Lecture01-eng.tex", rb"\begin{frame}{Course Setup}Intro\end{frame}"),
        ("uploads/Lecture02_old.tex", rb"\begin{frame}{Old Version}Ignore\end{frame}"),
        ("uploads/Lecture02-eng.tex", rb"\begin{frame}{Bayes Classifier}Bayes\end{frame}"),
    ]:
        response = client.post(
            "/admin/courses/demo-ml-course/materials",
            data={"path": path},
            files={"file": (Path(path).name, content)},
            headers=professor_headers(),
        )
        assert response.status_code == 200

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        response = client.get(
            "/admin/courses/demo-ml-course/lecture-schedule?first_lecture_date=2026-05-06",
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
    events = [json.loads(record.message) for record in caplog.records]
    schedule_events = [
        event for event in events if event.get("span") == "lecturepilot.course_schedule_generation"
    ]
    assert [event["event"] for event in schedule_events] == [
        "observability.span_started",
        "observability.span_finished",
    ]
    assert schedule_events[-1]["lecture_count"] == 2
    assert schedule_events[-1]["source_count"] == 3


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
        headers={**professor_headers(), "Idempotency-Key": "draft-request-key-0007"},
    )
    assert draft.status_code == 200
    assert draft.json()["course_id"] == "demo-ml-course"
    assert draft.json()["lecture_id"] == "lecture-07"
    assert draft.json()["source_kind"] == "generated"
    assert "workspace_path" not in draft.json()

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


def test_full_course_draft_uses_matching_lecture_source(tmp_path: Path) -> None:
    client = _client(tmp_path)
    planner = _RecordingCoursePlanner()
    client.app.state.course_planner = planner
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
                    "material_path": "Lecture01-eng.tex",
                },
                {
                    "number": "02",
                    "title": "Generalization",
                    "date": "2026-05-13",
                    "material_path": "Lecture02-eng.tex",
                },
            ],
        },
        headers=professor_headers(),
    )
    assert response.status_code == 200
    for path, title in [
        ("Lecture01-eng.tex", "Course Setup"),
        ("Lecture02-eng.tex", "Generalization"),
    ]:
        upload = client.post(
            "/admin/courses/demo-ml-course/materials",
            data={"path": path},
            files={
                "file": (
                    Path(path).name,
                    (
                        f"\\begin{{frame}}{{{title}}}"
                        f"This lecture introduces {title} with enough source evidence."
                        "\\end{frame}"
                    ).encode(),
                )
            },
            headers=professor_headers(),
        )
        assert upload.status_code == 200

    draft = client.post(
        "/admin/courses/demo-ml-course/lectures/lecture-02/canvas/draft",
        headers={**professor_headers(), "Idempotency-Key": "draft-request-key-0002"},
    )

    assert draft.status_code == 200
    assert planner.seen_source_refs == ["Lecture02-eng.tex"]
    assert draft.json()["source_ref"] == "planned Lecture02-eng.tex"


def test_course_canvas_draft_can_use_markdown_text_and_pdf_without_latex(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.course_planner = _FakeMixedSourcePlanner()
    _create_workspace(client, "Mixed Source Course", "01", "Evidence and Risk")

    uploads = [
        (
            "notes/overview.md",
            b"# Evidence Update\n\nBayes combines prior belief with likelihood evidence.",
        ),
        (
            "notes/risk.txt",
            b"Risk-sensitive classification changes decisions when errors have different costs.",
        ),
        (
            "slides/risk.pdf",
            _pdf_source("PDF slide text explains posterior risk and reject decisions."),
        ),
        ("figures/risk.png", b"\x89PNG\r\n\x1a\n"),
        (
            "figures/risk.png.json",
            b'{"title":"Risk regions","description":"Posterior and loss threshold graphic"}',
        ),
        ("videos/decision.mp4", b"\x00\x00\x00\x18ftypmp42"),
        (
            "videos/decision.json",
            b'{"title":"Decision walkthrough","description":"Professor-provided media"}',
        ),
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
        headers={**professor_headers(), "Idempotency-Key": "draft-request-key-mixed-0001"},
    )

    assert draft.status_code == 200
    assert draft.json()["source_kind"] == "generated"
    assert (
        draft.json()["source_ref"]
        == "course planner from notes/overview.md, notes/risk.txt, slides/risk.pdf"
    )
    publish = client.post(
        "/admin/courses/mixed-source-course/lectures/lecture-01/canvas/publish",
        headers=professor_headers(),
    )
    assert publish.status_code == 200

    asset = client.get(
        "/course-assets/mixed-source-course/lecture-01/figures/risk.png",
        headers=student_headers(),
    )
    assert asset.status_code == 200
    assert asset.content.startswith(b"\x89PNG")
    video = client.get(
        "/course-assets/mixed-source-course/lecture-01/videos/decision.mp4",
        headers=student_headers(),
    )
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
    return rb"""
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
        assert source_document.source_kind == "latex"
        return source_document.model_copy(
            update={
                "source_kind": "generated",
                "source_ref": "course planner from Lecture07.tex",
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


class _RecordingCoursePlanner:
    def __init__(self) -> None:
        self.seen_source_refs: list[str] = []

    async def plan_canvas(self, source_document):
        self.seen_source_refs.append(source_document.source_ref)
        return source_document.model_copy(
            update={
                "source_kind": "generated",
                "source_ref": f"planned {source_document.source_ref}",
            }
        )


class _FakeLectureSchedulePlanner:
    def __init__(self) -> None:
        self.last_first_lecture_date = None
        self.last_paths: list[str] = []
        self.last_requested_count = None

    async def propose_schedule(
        self, *, course_id, files, roots, first_lecture_date, requested_count
    ):
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


class _FakeLoginAdapter:
    def authenticate(self, *, username: str, password: str, term: str):
        return pending_university_login(
            UniversityLoginResult(
                username=username,
                email=f"{username}@uni-tuebingen.de",
                term=term,
                courses=[
                    ExternalCourseCandidate(
                        source="alma",
                        external_course_id="unit:4193",
                        title="INFO4193 Natural Language Processing",
                        organization="Fachbereich Informatik",
                        term=term,
                    )
                ],
                sources_checked={"alma"},
            )
        )


def _course_titles(payload: dict) -> list[str]:
    return [course["title"] for course in payload["courses"]]


class _FakeMixedSourcePlanner:
    async def plan_canvas(self, source_document):
        evidence = "\n".join(
            block.text or "" for section in source_document.sections for block in section.blocks
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
        media = {
            block.asset_path: block
            for section in source_document.sections
            for block in section.blocks
            if block.asset_path in {"figures/risk.png", "videos/decision.mp4"}
        }
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
                            ),
                            media["figures/risk.png"],
                            media["videos/decision.mp4"],
                        ],
                    )
                ],
            }
        )
