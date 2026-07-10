from pathlib import Path

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    CanvasCommand,
    CanvasSectionPlacement,
    QualityGateDecision,
    QualityGateStatus,
)
from auth_helpers import professor_headers, student_headers


def test_canvas_endpoint_loads_private_course_source_for_student(tmp_path: Path) -> None:
    app = create_app()
    app.state.canvas_workspace = _workspace(tmp_path)
    client = TestClient(app)

    response = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas?user_id=student01",
        headers=student_headers("student01"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Bayesian Decision Theory"
    assert payload["source_ref"] == "Lecture03-eng.tex"
    assert payload["sections"][0]["id"] == "bayesian-decision-theory-the-aim"
    assert "workspace_path" not in payload


def test_agent_appended_canvas_section_persists_for_same_student(tmp_path: Path) -> None:
    app = create_app()
    app.state.canvas_workspace = _workspace(tmp_path)
    app.state.agent_harness = _AppendingHarness()
    client = TestClient(app)

    response = client.post(
        "/agent/turn",
        headers=student_headers("student01"),
        json={
            "course_id": "martius-ml",
            "lecture_id": "lecture-03",
            "attendance": "absent",
            "message": "Explain this with soccer.",
            "canvas_state": {"focused_section_id": "bayes-formula"},
        },
    )
    same_student = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas?user_id=student01",
        headers=student_headers("student01"),
    )
    other_student = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas?user_id=student02",
        headers=student_headers("student01"),
    )
    professor_view = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas?user_id=student02",
        headers=professor_headers(),
    )

    assert response.status_code == 200
    assert _next_section_id(same_student.json(), "bayesian-decision-theory-the-aim") == "student-soccer-bayes-example"
    assert other_student.status_code == 200
    assert _next_section_id(other_student.json(), "bayesian-decision-theory-the-aim") == "student-soccer-bayes-example"
    assert professor_view.status_code == 403
    lecture_root = app.state.canvas_workspace.layout.user_lecture_root(
        "student01",
        "martius-ml",
        "lecture-03",
    )
    user_root = app.state.canvas_workspace.layout.user_root("student01")
    assert (user_root / "memories" / "global.md").exists()
    assert (user_root / "memories" / "preferences.json").exists()
    assert (user_root / "memories" / "memory-trace.jsonl").exists()
    assert (user_root / "courses" / "martius-ml" / "memories" / "course.md").exists()
    assert (user_root / "courses" / "martius-ml" / "memories" / "memory-trace.jsonl").exists()
    assert '"attendance": "absent"' in (lecture_root / "attendance.json").read_text()
    assert "demo-gate" in (lecture_root / "gates.json").read_text()
    component_file = lecture_root / "canvas" / "components" / "student-risk-check.yaml"
    assert component_file.exists()
    assert "id: posterior-risk" in component_file.read_text(encoding="utf-8")


def test_learner_workspace_reset_clears_selected_scopes(tmp_path: Path) -> None:
    app = create_app()
    app.state.canvas_workspace = _workspace(tmp_path)
    app.state.agent_harness = _AppendingHarness()
    client = TestClient(app)
    client.post(
        "/agent/turn",
        headers=student_headers("student01"),
        json={
            "course_id": "martius-ml",
            "lecture_id": "lecture-03",
            "attendance": "absent",
            "message": "Explain this with soccer.",
            "canvas_state": {"focused_section_id": "bayesian-decision-theory-the-aim"},
        },
    )
    layout = app.state.canvas_workspace.layout
    course_root = layout.user_course_root("student01", "martius-ml")
    lecture_root = layout.user_lecture_root("student01", "martius-ml", "lecture-03")
    (course_root / "progress.json").write_text('{"attempts": [], "active_tasks": []}', encoding="utf-8")

    response = client.post(
        "/courses/martius-ml/learner-workspace/reset",
        headers=student_headers("student01"),
        json={
            "reset_canvas": True,
            "reset_course_memory": True,
            "reset_progress": False,
        },
    )
    same_student = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas?user_id=student01",
        headers=student_headers("student01"),
    )

    assert response.status_code == 200
    assert "student-soccer-bayes-example" not in _section_ids(same_student.json())
    assert not (course_root / "memories").exists()
    assert (course_root / "progress.json").exists()
    assert (lecture_root / "attendance.json").exists()
    assert (lecture_root / "gates.json").exists()

    progress_response = client.post(
        "/courses/martius-ml/learner-workspace/reset",
        headers=student_headers("student01"),
        json={
            "reset_canvas": False,
            "reset_course_memory": False,
            "reset_progress": True,
        },
    )

    assert progress_response.status_code == 200
    assert not (course_root / "progress.json").exists()
    assert not (lecture_root / "attendance.json").exists()
    assert not (lecture_root / "gates.json").exists()


def test_canvas_endpoint_requires_authenticated_learner_identity(tmp_path: Path) -> None:
    app = create_app()
    app.state.canvas_workspace = _workspace(tmp_path)
    client = TestClient(app)

    response = client.get("/courses/martius-ml/lectures/lecture-03/canvas?user_id=student01")

    assert response.status_code == 401


class _AppendingHarness:
    async def run_turn(self, turn: AgentTurnInput) -> AgentTurnResult:
        assert turn.user_memory.preferences == {}
        section = CanvasSection(
            id="student-soccer-bayes-example",
            title="Soccer scouting example",
            blocks=[
                CanvasBlock(
                    id="student-soccer-bayes-example-p-1",
                    type="paragraph",
                    text="Student-specific explanation.",
                ),
                CanvasBlock(
                    id="student-risk-check",
                    type="component",
                    component_id="student-risk-check",
                    component_type="single_choice_quiz",
                    component_version=1,
                    caption="Risk check",
                    text="Which value changes the expected-risk decision?",
                    items=["The posterior-weighted loss", "The slide number"],
                    option_ids=["posterior-risk", "slide-number"],
                    answer_index=0,
                )
            ],
        )
        return AgentTurnResult(
            message="Added a student-specific canvas section.",
            canvas_commands=[
                CanvasCommand(
                    type="append_section",
                    section_id=section.id,
                    section=section,
                    placement=CanvasSectionPlacement(section_id="bayesian-decision-theory-the-aim"),
                )
            ],
            quality_gate=QualityGateDecision(
                gate_id="demo-gate",
                status=QualityGateStatus.NEEDS_EVIDENCE,
                reason="The student still needs one concrete explanation.",
            ),
            model="local-guided-preview",
        )


def _section_ids(payload: dict) -> list[str]:
    return [section["id"] for section in payload["sections"]]


def _next_section_id(payload: dict, section_id: str) -> str | None:
    ids = _section_ids(payload)
    index = ids.index(section_id)
    return ids[index + 1] if index + 1 < len(ids) else None


def _workspace(tmp_path: Path) -> CanvasWorkspace:
    material_root = tmp_path / "course"
    material_root.mkdir()
    (material_root / "Lecture03-eng.tex").write_text(
        r"""
\mytitle[29 April, 2025]{3}{Bayesian Decision Theory}
\begin{frame}{Bayesian Decision Theory: The Aim}
Bayesian decision theory connects evidence, posterior probabilities, and decisions.
\end{frame}
""",
        encoding="utf-8",
    )
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )
    workspace.write_course_canvas(
        workspace.source_document(
            course_id="martius-ml",
            lecture_id="lecture-03",
            workspace_path=str(tmp_path / "published" / "index.md"),
        )
    )
    return workspace
