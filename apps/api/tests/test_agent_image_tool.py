from __future__ import annotations

from canvas_workspace_fixtures import write_course_source
from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.image_generation import GeneratedImage


def test_generate_image_writes_real_learner_canvas_section(tmp_path) -> None:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=write_course_source(tmp_path),
    )
    workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    executor = AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u1",
        image_generator=_FakeImageGenerator(),
    )

    result = executor.execute(
        "generate_image",
        {
            "prompt": "Visualize prior times likelihood becoming posterior.",
            "section_id": "posterior-visual",
            "filename": "posterior-visual",
        },
    )

    assert result["ok"] is True
    assert result["asset_url"].endswith("/student-assets/posterior-visual.png")
    document = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    section = document.sections[-1]
    assert section.id == "posterior-visual-md"
    assert section.blocks[0].type == "asset"
    assert section.blocks[0].asset_url == result["asset_url"]
    assert executor.canvas_update_commands()[-1].section_id == "posterior-visual-md"


class _FakeImageGenerator:
    def generate_infographic(self, *, prompt, section):
        return GeneratedImage(
            content=b"fake-png",
            mime_type="image/png",
            extension="png",
            caption=f"Infographic for {section.id}",
            provider="fake",
            model="fake-image-model",
        )
