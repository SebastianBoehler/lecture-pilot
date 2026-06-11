from pathlib import Path

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.models import (
    AgentTurnInput,
    AgentTurnResult,
    CanvasCommand,
    QualityGateDecision,
    QualityGateStatus,
)


def test_canvas_endpoint_loads_private_course_source_for_student(tmp_path: Path) -> None:
    app = create_app()
    app.state.canvas_workspace = _workspace(tmp_path)
    client = TestClient(app)

    response = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas?user_id=student01"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Bayesian Decision Theory"
    assert payload["source_ref"] == "Lecture03-eng.tex"
    assert payload["sections"][0]["id"] == "bayesian-decision-theory-the-aim"
    assert "student01" not in payload["workspace_path"]


def test_agent_appended_canvas_section_persists_for_same_student(tmp_path: Path) -> None:
    app = create_app()
    app.state.canvas_workspace = _workspace(tmp_path)
    app.state.agent_harness = _AppendingHarness()
    client = TestClient(app)

    response = client.post(
        "/agent/turn",
        json={
            "user_id": "student01",
            "course_id": "martius-ml",
            "lecture_id": "lecture-03",
            "attendance": "absent",
            "message": "Explain this with soccer.",
            "canvas_state": {"focused_section_id": "bayes-formula"},
        },
    )
    same_student = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas?user_id=student01"
    )
    other_student = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas?user_id=student02"
    )

    assert response.status_code == 200
    assert _section_ids(same_student.json())[-1] == "student-soccer-bayes-example"
    assert "student-soccer-bayes-example" not in _section_ids(other_student.json())
    lecture_root = app.state.canvas_workspace.layout.user_lecture_root(
        "student01",
        "martius-ml",
        "lecture-03",
    )
    user_root = app.state.canvas_workspace.layout.user_root("student01")
    assert (user_root / "memories" / "global.md").exists()
    assert (user_root / "memories" / "preferences.json").exists()
    assert '"attendance": "absent"' in (lecture_root / "attendance.json").read_text()
    assert "demo-gate" in (lecture_root / "gates.json").read_text()
    component_file = lecture_root / "canvas" / "components" / "student-risk-check.yaml"
    assert component_file.exists()
    assert "id: posterior-risk" in component_file.read_text(encoding="utf-8")


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
    return CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=material_root,
    )
