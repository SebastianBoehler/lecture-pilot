from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_schedule_store import write_course_workspace
from lecturepilot.models import (
    AgentTurnResult,
    CanvasCommand,
    CanvasSectionPlacement,
    Course,
    CourseWorkspaceResult,
    Lecture,
    QualityGateDecision,
    QualityGateStatus,
)
from lecturepilot.professor_preview import professor_preview_user_id


PREVIEW_HEADER = {"X-LecturePilot-Learner-Preview": "professor"}


def test_professor_preview_persists_private_learner_state_without_analytics(
    tmp_path: Path,
) -> None:
    client = _client(tmp_path)
    client.app.state.agent_harness = _PreviewHarness()
    quota = _QuotaProbe()
    client.app.state.usage_quota = quota
    professor = {**professor_headers("prof-1"), **PREVIEW_HEADER}

    blocked = client.get(
        "/courses/demo-course/lectures/lecture-01/canvas",
        headers=professor_headers("prof-1"),
    )
    opened = client.get(
        "/courses/demo-course/lectures/lecture-01/canvas",
        headers=professor,
    )
    turn = client.post(
        "/agent/turn",
        headers=professor,
        json={
            "course_id": "demo-course",
            "lecture_id": "lecture-01",
            "attendance": "present",
            "message": "Remember this explanation and test the canvas.",
            "canvas_state": {"focused_section_id": "risk"},
        },
    )
    persisted = client.get(
        "/courses/demo-course/lectures/lecture-01/canvas",
        headers=professor,
    )
    student = client.get(
        "/courses/demo-course/lectures/lecture-01/canvas",
        headers=student_headers("student-1", course_ids=["demo-course"]),
    )
    quiz = client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=professor,
        json={"attendance": "present", "block_id": "risk-quiz", "option_index": 1},
    )
    analytics = client.get(
        "/admin/courses/demo-course/lectures/lecture-01/analytics",
        headers=professor_headers("prof-1"),
    )
    managed_courses = client.get("/admin/courses", headers=professor_headers("prof-1"))

    assert blocked.status_code == 403
    assert opened.status_code == 200
    assert turn.status_code == 200
    assert "professor-preview-note" in _section_ids(persisted.json())
    assert "professor-preview-note" not in _section_ids(student.json())
    assert quiz.status_code == 200
    assert quiz.json()["correct"] is True
    assert analytics.json()["total_events"] == 0
    assert managed_courses.json()[0]["published_lecture_ids"] == ["lecture-01"]
    assert quota.reserved_user_ids == ["prof-1"]
    assert quota.released_user_ids == ["prof-1"]

    preview_user_id = professor_preview_user_id("prof-1", "demo-course")
    layout = client.app.state.canvas_workspace.layout
    preview_root = layout.user_root(preview_user_id)
    assert preview_root.parent.parent == layout.root / "previews"
    assert (preview_root / "memories" / "global.md").exists()
    assert (
        preview_root / "courses" / "demo-course" / "lectures" / "lecture-01" / "attendance.json"
    ).exists()
    assert not layout.user_root("student-1").joinpath("memories", "global.md").exists()


def test_professor_preview_reset_only_clears_the_professor_sandbox(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.agent_harness = _PreviewHarness()
    professor = {**professor_headers("prof-1"), **PREVIEW_HEADER}
    turn_body = {
        "course_id": "demo-course",
        "lecture_id": "lecture-01",
        "attendance": "present",
        "message": "Add a private preview note.",
        "canvas_state": {"focused_section_id": "risk"},
    }
    assert client.post("/agent/turn", headers=professor, json=turn_body).status_code == 200

    reset = client.post(
        "/courses/demo-course/learner-workspace/reset",
        headers=professor,
        json={"reset_canvas": True, "reset_course_memory": True, "reset_progress": True},
    )
    reopened = client.get(
        "/courses/demo-course/lectures/lecture-01/canvas",
        headers=professor,
    )

    assert reset.status_code == 200
    assert "professor-preview-note" not in _section_ids(reopened.json())
    preview_user_id = professor_preview_user_id("prof-1", "demo-course")
    assert not client.app.state.canvas_workspace.layout.user_memories_dir(preview_user_id).exists()


def test_professor_preview_readiness_progress_is_not_counted_as_a_learner(tmp_path: Path) -> None:
    client = _client(tmp_path)
    professor = {**professor_headers("prof-1"), **PREVIEW_HEADER}
    check = client.get("/courses/demo-course/exam-readiness", headers=professor)
    answers = [
        (
            {"question_id": question["id"], "selected_index": 1}
            if question["kind"] == "multiple_choice"
            else {"question_id": question["id"], "text": "Expected risk includes loss."}
        )
        for question in check.json()["questions"]
    ]

    attempt = client.post(
        "/courses/demo-course/exam-readiness/attempts",
        headers=professor,
        json={"answers": answers},
    )
    summary = client.get(
        "/admin/courses/demo-course/exam-readiness/summary",
        headers=professor_headers("prof-1"),
    )

    assert check.status_code == 200
    assert attempt.status_code == 200
    assert summary.json()["total_attempts"] == 0
    assert summary.json()["unique_learners"] == 0
    preview_user_id = professor_preview_user_id("prof-1", "demo-course")
    progress = (
        client.app.state.canvas_workspace.layout.user_course_root(
            preview_user_id,
            "demo-course",
        )
        / "progress.json"
    )
    assert progress.exists()


def test_student_cannot_request_professor_preview(tmp_path: Path) -> None:
    response = _client(tmp_path).get(
        "/courses/demo-course/lectures/lecture-01/canvas",
        headers={
            **student_headers("student-1", course_ids=["demo-course"]),
            **PREVIEW_HEADER,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Professor access is required."


class _PreviewHarness:
    async def run_turn(self, _turn, **_kwargs) -> AgentTurnResult:
        section = CanvasSection(
            id="professor-preview-note",
            title="Private preview note",
            blocks=[
                CanvasBlock(
                    id="professor-preview-note-p",
                    type="paragraph",
                    text="This belongs only to the professor preview.",
                )
            ],
        )
        return AgentTurnResult(
            message="Added the preview note.",
            canvas_commands=[
                CanvasCommand(
                    type="append_section",
                    section_id=section.id,
                    section=section,
                    placement=CanvasSectionPlacement(section_id="risk"),
                )
            ],
            quality_gate=QualityGateDecision(
                gate_id="risk-gate",
                status=QualityGateStatus.PASSED,
                reason="Preview evidence was sufficient.",
            ),
            model="test/model",
        )


class _QuotaProbe:
    def __init__(self) -> None:
        self.reserved_user_ids: list[str] = []
        self.released_user_ids: list[str] = []

    def reserve_turn(self, *, tenant_id: str, user_id: str, course_id: str) -> bool:
        self.reserved_user_ids.append(user_id)
        return True

    def release_turn(self, *, tenant_id: str, user_id: str, course_id: str) -> None:
        self.released_user_ids.append(user_id)

    def consume_image(self, *, tenant_id: str, user_id: str, course_id: str) -> None:
        raise AssertionError("Image generation was not expected.")


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    write_course_workspace(
        app.state.canvas_workspace.course_media_root("demo-course"),
        CourseWorkspaceResult(
            course=Course(
                id="demo-course",
                title="Demo course",
                professor="Professor Demo",
                term="Sommer 2026",
            ),
            lectures=[
                Lecture(
                    id="lecture-01",
                    course_id="demo-course",
                    title="Risk",
                    date=date(2026, 6, 1),
                )
            ],
            active_lecture_id="lecture-01",
        ),
    )
    app.state.canvas_workspace.write_course_canvas(_document())
    return TestClient(app)


def _document() -> CanvasDocument:
    return CanvasDocument(
        id="demo-course-lecture-01",
        course_id="demo-course",
        lecture_id="lecture-01",
        title="Risk",
        source_kind="generated",
        source_ref="lecture-01.tex",
        workspace_path="course/canvas/index.md",
        sections=[
            CanvasSection(
                id="risk",
                title="Risk",
                blocks=[
                    CanvasBlock(
                        id="risk-quiz",
                        type="quiz",
                        text="Which quantity should be minimized?",
                        items=["Posterior", "Expected risk"],
                        answer_index=1,
                    )
                ],
            )
        ],
    )


def _section_ids(payload: dict) -> list[str]:
    return [section["id"] for section in payload["sections"]]
