from __future__ import annotations

from canvas_workspace_fixtures import write_course_source
from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.canvas_signatures import official_canvas_signature
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.image_generation import GeneratedImage
from lecturepilot.models import CanvasSectionPlacement


def test_generate_image_prefers_the_focused_learner_section(tmp_path) -> None:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=write_course_source(tmp_path),
    )
    workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    setup = AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u1",
    )
    setup.execute(
        "write",
        {
            "path": "/lecture/canvas/student/prior-notes.md",
            "content": "# Prior Notes\n\nThe prior records belief before evidence.",
        },
    )
    focused = setup.execute(
        "write",
        {
            "path": "/lecture/canvas/student/regression-tasks.md",
            "content": "# Regression Tasks\n\nRegression predicts a continuous target.",
        },
    )
    executor = AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u1",
        image_generator=_FakeImageGenerator(),
        initial_focus_section_id=focused["section_id"],
    )

    result = executor.execute(
        "generate_image",
        {"prompt": "Create a compact teaching visual.", "filename": "focused-visual"},
    )

    assert result["ok"] is True
    assert result["section_id"] == focused["section_id"]
    assert result["target_path"] == focused["path"]


def test_official_target_resolves_to_its_learner_extension_without_mutating_source(
    tmp_path,
) -> None:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=write_course_source(tmp_path),
    )
    before = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    official = next(section for section in before.sections if "bayes" in section.id)
    learner = CanvasSection(
        id="student-bayes-explanation",
        title="Bayes explanation",
        source_ref="student workspace",
        blocks=[
            CanvasBlock(
                id="student-bayes-explanation-p-1",
                type="paragraph",
                text="Prior and likelihood combine into the posterior.",
            )
        ],
    )
    workspace.apply_sections(
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u1",
        sections=[learner],
        placements={
            learner.id: CanvasSectionPlacement(mode="after_section", section_id=official.id)
        },
    )
    executor = AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u1",
        image_generator=_FakeImageGenerator(),
        initial_focus_section_id=official.id,
    )

    result = executor.execute(
        "generate_image",
        {
            "prompt": "Create a visual for the focused concept.",
            "section_id": official.id,
        },
    )

    assert result["ok"] is True
    assert result["section_id"] == learner.id
    assert "/student/" in result["target_path"]
    after = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    assert official_canvas_signature(after) == official_canvas_signature(before)


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
