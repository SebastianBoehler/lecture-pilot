from pathlib import Path

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.models import AgentTurnInput, AgentTurnResult, CanvasCommand
from lecturepilot.providers import DEFAULT_MODEL
from auth_helpers import student_headers
from canvas_workspace_fixtures import published_course_canvas


def test_agent_turn_materializes_infographic_asset(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LECTUREPILOT_MODEL", DEFAULT_MODEL)
    app = create_app()
    app.state.canvas_workspace = _published_workspace(tmp_path)
    app.state.canvas_workspace.image_generator = _FakeImageGenerator()
    app.state.agent_harness = _InfographicHarness()
    client = TestClient(app)

    response = client.post(
        "/agent/turn",
        headers=student_headers("student01"),
        json={
            "course_id": "martius-ml",
            "lecture_id": "lecture-03",
            "attendance": "absent",
            "message": "Create a real infographic image for Bayes as soccer scouting.",
            "canvas_state": {"focused_section_id": "bayes-formula"},
        },
    )

    assert response.status_code == 200
    section = response.json()["canvas_commands"][0]["section"]
    asset = section["blocks"][0]
    assert asset["type"] == "asset"
    assert asset["asset_path"].endswith(".png")
    assert asset["asset_url"].startswith("/workspace-assets/martius-ml/lecture-03/")
    assert asset["caption"] == "Generated with fake-image-model as a teaching infographic"

    unauthenticated_asset_response = client.get(asset["asset_url"])
    assert unauthenticated_asset_response.status_code == 401

    asset_response = client.get(asset["asset_url"], headers=student_headers("student01"))
    assert asset_response.status_code == 200
    assert asset_response.content == b"fake-png"

    denied_asset_response = client.get(asset["asset_url"], headers=student_headers("student02"))
    assert denied_asset_response.status_code == 403

    reloaded = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas",
        headers=student_headers("student01"),
    ).json()
    student_section = next(item for item in reloaded["sections"] if item["id"] == section["id"])
    assert student_section["blocks"][0]["asset_url"] == asset["asset_url"]

    other_student = client.get(
        "/courses/martius-ml/lectures/lecture-03/canvas",
        headers=student_headers("student02"),
    ).json()
    assert all(item["id"] != section["id"] for item in other_student["sections"])


def test_agent_turn_requires_image_provider_for_infographics(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    app = create_app()
    app.state.canvas_workspace = _published_workspace(tmp_path)
    app.state.agent_harness = _InfographicHarness()
    client = TestClient(app)

    response = client.post(
        "/agent/turn",
        headers=student_headers("student01"),
        json={
            "course_id": "martius-ml",
            "lecture_id": "lecture-03",
            "attendance": "absent",
            "message": "Create a real infographic image for Bayes as soccer scouting.",
            "canvas_state": {"focused_section_id": "bayes-formula"},
        },
    )

    assert response.status_code == 502
    assert "text-to-image provider" in response.json()["detail"]


def test_workspace_asset_route_rejects_invalid_student_key(tmp_path: Path) -> None:
    app = create_app()
    app.state.canvas_workspace = _published_workspace(tmp_path)
    client = TestClient(app)

    response = client.get(
        "/workspace-assets/martius-ml/lecture-03/not-a-hash/student-assets/x.svg",
        headers=student_headers("student01"),
    )

    assert response.status_code == 403


class _InfographicHarness:
    async def run_turn(self, turn: AgentTurnInput) -> AgentTurnResult:
        section = CanvasSection(
            id="student-bayes-soccer-infographic",
            title="Bayes soccer scouting flow",
            source_ref="student workspace",
            blocks=[
                CanvasBlock(
                    id="student-bayes-soccer-infographic-list-1",
                    type="list",
                    items=[
                        "Prior: baseline chance a player fits the team",
                        "Evidence: scouting reports and match observations",
                        "Likelihood: how expected those reports are if the player fits",
                        "Decision: compare posterior belief with signing risk",
                    ],
                )
            ],
        )
        return AgentTurnResult(
            message="I added a generated infographic to the canvas.",
            canvas_commands=[
                CanvasCommand(
                    type="append_section",
                    section_id=section.id,
                    section=section,
                )
            ],
            model=DEFAULT_MODEL,
        )


class _FakeImageGenerator:
    def generate_infographic(self, *, prompt: str, section: CanvasSection):
        from lecturepilot.image_generation import GeneratedImage

        assert "soccer scouting" in prompt
        assert section.title == "Bayes soccer scouting flow"
        return GeneratedImage(
            content=b"fake-png",
            mime_type="image/png",
            extension="png",
            caption="Generated with fake-image-model as a teaching infographic",
            provider="fake",
            model="fake-image-model",
        )


def _write_course_source(tmp_path: Path) -> Path:
    material_root = tmp_path / "course"
    material_root.mkdir()
    for index, title in [
        ("01", "Introduction"),
        ("02", "Linear Models and Generalization"),
        ("03", "Bayesian Decision Theory"),
    ]:
        (material_root / f"Lecture{index}-eng.tex").write_text(
            rf"""
\mytitle[6 May, 2026]{{{int(index)}}}{{{title}}}
\begin{{frame}}{{{title}}}
Bayes formula turns evidence into a posterior for a classification problem.
\[
P(C\mid X) = \frac{{P(X\mid C)P(C)}}{{P(X)}}
\]
\end{{frame}}
""",
            encoding="utf-8",
        )
    return material_root


def _published_workspace(tmp_path: Path) -> CanvasWorkspace:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=_write_course_source(tmp_path),
    )
    workspace.write_course_canvas(published_course_canvas("martius-ml", "lecture-03"))
    return workspace
