from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers, student_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.models import AgentTurnResult, QualityGateDecision, QualityGateStatus


def test_quiz_answers_are_recorded_as_aggregate_lecture_analytics(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=student_headers("student-a"),
        json={
            "user_id": "student-a",
            "attendance": "present",
            "block_id": "risk-check",
            "option_index": 1,
        },
    )
    assert response.status_code == 200
    assert response.json()["correct"] is True

    second = client.post(
        "/courses/demo-course/lectures/lecture-01/analytics/quiz-answer",
        headers=student_headers("student-b"),
        json={
            "user_id": "student-b",
            "attendance": "absent",
            "block_id": "risk-check",
            "option_index": 0,
        },
    )
    assert second.status_code == 200
    assert second.json()["correct"] is False

    summary = client.get(
        "/admin/courses/demo-course/lectures/lecture-01/analytics",
        headers=professor_headers(),
    )

    assert summary.status_code == 200
    payload = summary.json()
    assert payload["total_events"] == 2
    quiz = payload["quizzes"][0]
    assert quiz["component_id"] == "risk-check"
    assert quiz["total_attempts"] == 2
    assert quiz["unique_learners"] == 2
    assert quiz["correct_attempts"] == 1
    assert quiz["correct_rate"] == 0.5
    assert quiz["attendance_split"] == {"absent": 1, "present": 1}
    assert [option["selections"] for option in quiz["options"]] == [1, 1, 0]
    assert quiz["options"][1]["correct"] is True


def test_students_cannot_read_professor_analytics(tmp_path: Path) -> None:
    client = _client(tmp_path)

    response = client.get(
        "/admin/courses/demo-course/lectures/lecture-01/analytics",
        headers=student_headers("student-a"),
    )

    assert response.status_code == 403


def test_quality_gate_turns_are_recorded_in_analytics(tmp_path: Path) -> None:
    client = _client(tmp_path)
    client.app.state.agent_harness = _GateHarness()

    response = client.post(
        "/agent/turn",
        headers=student_headers("student-a"),
        json={
            "user_id": "student-a",
            "course_id": "demo-course",
            "lecture_id": "lecture-01",
            "attendance": "present",
            "message": "I can connect posterior and risk.",
            "canvas_state": {"focused_section_id": "risk"},
        },
    )
    assert response.status_code == 200

    summary = client.get(
        "/admin/courses/demo-course/lectures/lecture-01/analytics",
        headers=professor_headers(),
    )

    assert summary.status_code == 200
    gate = summary.json()["gates"][0]
    assert gate["gate_id"] == "risk-gate"
    assert gate["status_counts"] == {"passed": 1}
    assert gate["attendance_split"] == {"present": 1}
    assert gate["unique_learners"] == 1


def _client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    app.state.canvas_workspace.write_course_canvas(_canvas_document(tmp_path))
    return TestClient(app)


def _canvas_document(tmp_path: Path) -> CanvasDocument:
    return CanvasDocument(
        id="demo-course-lecture-01",
        course_id="demo-course",
        lecture_id="lecture-01",
        title="Risk lecture",
        source_kind="generated",
        source_ref="test source",
        workspace_path=str(tmp_path / "canvas" / "index.md"),
        sections=[
            CanvasSection(
                id="risk",
                title="Risk decisions",
                source_ref="test source",
                blocks=[
                    CanvasBlock(
                        id="risk-check",
                        type="component",
                        component_id="risk-check",
                        component_type="single_choice_quiz",
                        caption="Risk threshold check",
                        text="Which action minimizes expected risk?",
                        items=["Use the largest class prior.", "Use posterior-weighted loss.", "Ignore costs."],
                        option_ids=["prior-only", "posterior-loss", "ignore-cost"],
                        answer_index=1,
                    )
                ],
            )
        ],
    )


class _GateHarness:
    async def run_turn(self, *_args, **_kwargs):
        return AgentTurnResult(
            message="Gate passed.",
            model="test-harness",
            quality_gate=QualityGateDecision(
                gate_id="risk-gate",
                status=QualityGateStatus.PASSED,
                reason="Student connected posterior and risk.",
            ),
        )
