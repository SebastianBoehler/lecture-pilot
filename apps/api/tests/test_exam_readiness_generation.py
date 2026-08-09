from pathlib import Path

from auth_helpers import professor_headers, student_headers
from canvas_workspace_fixtures import publish_course_canvas
from lecturepilot.canvas_workspace import CanvasWorkspace
from test_exam_readiness import _client, _document


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
    publish_course_canvas(
        workspace, _document("lecture-03", "Bayesian Decision Theory", with_quiz=True)
    )
    publish_course_canvas(workspace, _document("lecture-04", "Linear Models", with_quiz=False))

    response = client.get("/courses/demo-ml-course/exam-readiness", headers=student_headers())

    assert response.status_code == 200
    payload = response.json()
    assert payload["course_id"] == "demo-ml-course"
    assert payload["published_lecture_count"] == 2
    assert {item["lecture_id"] for item in payload["coverage"]} == {"lecture-03", "lecture-04"}
    assert {question["kind"] for question in payload["questions"]} == {
        "multiple_choice",
        "open_ended",
    }
    quiz = next(item for item in payload["questions"] if item["kind"] == "multiple_choice")
    assert "answer_index" not in quiz
    assert "rubric" not in quiz
    assert quiz["lecture_title"] == "Bayesian Decision Theory"


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
    assert response.json()["detail"] == (
        "Publish at least one lecture canvas before running the exam readiness check."
    )
