from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_professor_creates_stable_course_workspace_ids(tmp_path: Path) -> None:
    client = _client(tmp_path)

    first = _create_workspace(client, "Demo ML Course", "03", "Bayesian Decision Theory")
    second = _create_workspace(client, "Robotics Seminar", "7", "Policy Gradients")

    assert first["course"]["id"] == "demo-ml-course"
    assert first["active_lecture_id"] == "lecture-03"
    assert first["lectures"][0]["course_id"] == "demo-ml-course"
    assert second["course"]["id"] == "robotics-seminar"
    assert second["active_lecture_id"] == "lecture-07"
    assert second["lectures"][0]["course_id"] == "robotics-seminar"


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

    student = client.get(
        "/courses/demo-ml-course/lectures/lecture-07/canvas?user_id=student01",
        headers=student_headers("student01"),
    )
    assert student.status_code == 200
    assert student.json()["sections"][0]["title"] == "Planner summary"


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


class _FakeCoursePlanner:
    async def plan_canvas(self, source_document):
        assert source_document.course_id == "demo-ml-course"
        assert source_document.lecture_id == "lecture-07"
        assert source_document.source_ref == "Lecture07.tex"
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
