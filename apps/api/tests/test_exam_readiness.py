from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_exam_readiness_uses_published_course_canvases(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Demo ML Course",
            "target": "full-course",
            "lectures": [
                {"number": "03", "title": "Bayesian Decision Theory", "date": "2026-05-20"},
                {"number": "04", "title": "Linear Models", "date": "2026-05-27"},
            ],
        },
        headers=professor_headers(),
    )
    workspace: CanvasWorkspace = client.app.state.canvas_workspace
    workspace.write_course_canvas(_document("lecture-03", "Bayesian Decision Theory", with_quiz=True))
    workspace.write_course_canvas(_document("lecture-04", "Linear Models", with_quiz=False))

    response = client.get("/courses/demo-ml-course/exam-readiness", headers=student_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["course_id"] == "demo-ml-course"
    assert payload["published_lecture_count"] == 2
    assert {item["lecture_id"] for item in payload["coverage"]} == {"lecture-03", "lecture-04"}
    assert any(question["kind"] == "multiple_choice" for question in payload["questions"])
    assert any(question["kind"] == "open_ended" for question in payload["questions"])
    quiz = next(question for question in payload["questions"] if question["kind"] == "multiple_choice")
    assert quiz["answer_index"] == 1
    assert quiz["lecture_title"] == "Bayesian Decision Theory"
    assert len([question for question in payload["questions"] if question["kind"] == "open_ended"]) >= 1


def test_exam_readiness_requires_published_canvases(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Demo ML Course",
            "target": "single-lecture",
            "lecture_number": "03",
            "lecture_title": "Bayesian Decision Theory",
        },
        headers=professor_headers(),
    )

    response = client.get("/courses/demo-ml-course/exam-readiness", headers=student_headers())

    assert response.status_code == 404
    assert response.json()["detail"] == "Publish at least one lecture canvas before running the exam readiness check."


def test_exam_readiness_filters_admin_sections_and_limits_mc_dominance(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Demo ML Course",
            "target": "full-course",
            "lectures": [
                {"number": "01", "title": "Intro", "date": "2026-05-06"},
                {"number": "02", "title": "Risk", "date": "2026-05-13"},
                {"number": "03", "title": "Bayes", "date": "2026-05-20"},
                {"number": "04", "title": "Classification", "date": "2026-05-27"},
            ],
        },
        headers=professor_headers(),
    )
    workspace: CanvasWorkspace = client.app.state.canvas_workspace
    for index in range(1, 5):
        workspace.write_course_canvas(_document(f"lecture-{index:02d}", f"Lecture {index}", with_quiz=True))

    response = client.get("/courses/demo-ml-course/exam-readiness", headers=student_headers())

    assert response.status_code == 200
    payload = response.json()
    assert not any("Admin Details" in question["section_title"] for question in payload["questions"])
    kinds = [question["kind"] for question in payload["questions"]]
    assert kinds.count("multiple_choice") <= 6
    assert kinds.count("open_ended") >= 3


def test_exam_readiness_attempt_is_persisted_in_learner_progress(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Demo ML Course",
            "target": "single-lecture",
            "lecture_number": "03",
            "lecture_title": "Bayesian Decision Theory",
        },
        headers=professor_headers(),
    )
    workspace: CanvasWorkspace = client.app.state.canvas_workspace
    workspace.write_course_canvas(_document("lecture-03", "Bayesian Decision Theory", with_quiz=True))

    response = client.post(
        "/courses/demo-ml-course/exam-readiness/attempts",
        headers=student_headers("student-a"),
        json={
            "answers": [
                {"question_id": "lecture-03:lecture-03-quiz", "selected_index": 0},
                {"question_id": "lecture-03:lecture-03-section:open", "text": "Bayes compares evidence."},
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["attempt_id"].startswith("attempt-")
    assert payload["score"] == 0
    assert payload["guidance_level"] == "scaffolded"
    assert payload["tasks"][0]["source_ref"] == "lecture-03.tex"
    progress_path = workspace.layout.user_course_root("student-a", "demo-ml-course") / "progress.json"
    assert progress_path.exists()
    assert not (workspace.layout.course_root("demo-ml-course") / "progress.json").exists()
    progress = progress_path.read_text(encoding="utf-8")
    assert "student-a" not in progress
    assert "Bayes compares evidence" not in progress
    assert "first_try" in progress


def test_exam_readiness_attempt_requires_authentication(tmp_path: Path) -> None:
    response = _client(tmp_path).post(
        "/courses/demo-ml-course/exam-readiness/attempts",
        json={"answers": [{"question_id": "lecture-03:lecture-03-quiz", "selected_index": 0}]},
    )

    assert response.status_code == 401


def test_exam_readiness_attempts_are_user_isolated(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Demo ML Course",
            "target": "single-lecture",
            "lecture_number": "03",
            "lecture_title": "Bayesian Decision Theory",
        },
        headers=professor_headers(),
    )
    workspace: CanvasWorkspace = client.app.state.canvas_workspace
    workspace.write_course_canvas(_document("lecture-03", "Bayesian Decision Theory", with_quiz=True))

    for user_id in ("student-a", "student-b"):
        response = client.post(
            "/courses/demo-ml-course/exam-readiness/attempts",
            headers=student_headers(user_id),
            json={
                "answers": [
                    {"question_id": "lecture-03:lecture-03-quiz", "selected_index": 1},
                    {"question_id": "lecture-03:lecture-03-section:open", "text": "Expected risk uses costs."},
                ]
            },
        )
        assert response.status_code == 200

    first = workspace.layout.user_course_root("student-a", "demo-ml-course") / "progress.json"
    second = workspace.layout.user_course_root("student-b", "demo-ml-course") / "progress.json"
    assert first.exists()
    assert second.exists()
    assert first != second


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    return TestClient(app)


def _document(lecture_id: str, title: str, *, with_quiz: bool) -> CanvasDocument:
    blocks = [
        CanvasBlock(
            id=f"{lecture_id}-p-1",
            type="paragraph",
            text=f"{title} connects evidence, model assumptions, and prediction decisions.",
        ),
        CanvasBlock(
            id=f"{lecture_id}-list",
            type="list",
            items=["Evidence", "Model assumption", "Decision rule"],
        ),
    ]
    if with_quiz:
        blocks.append(
            CanvasBlock(
                id=f"{lecture_id}-quiz",
                type="quiz",
                caption="Exam checkpoint",
                text="Which quantity should be minimized for cost-sensitive decisions?",
                items=["Posterior probability alone", "Expected risk", "Raw evidence count"],
                answer_index=1,
            )
        )
    return CanvasDocument(
        id=f"demo-ml-course-{lecture_id}",
        course_id="demo-ml-course",
        lecture_id=lecture_id,
        title=title,
        source_kind="generated",
        source_ref=f"{lecture_id}.tex",
        workspace_path="course/canvas/index.md",
        sections=[
            CanvasSection(
                id=f"{lecture_id}-admin",
                title="Please consult the German Lecture Slides for the Admin Details",
                source_ref=f"{lecture_id}.tex frames 1-2",
                blocks=[
                    CanvasBlock(
                        id=f"{lecture_id}-admin-quiz",
                        type="quiz",
                        text="Which deadline is listed in the admin slide?",
                        items=["Week 1", "Week 2", "Week 3"],
                        answer_index=0,
                    )
                ],
            ),
            CanvasSection(
                id=f"{lecture_id}-section",
                title=title,
                source_ref=f"{lecture_id}.tex",
                blocks=blocks,
            )
        ],
    )
