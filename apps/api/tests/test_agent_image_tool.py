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
    assert result["markdown"].endswith("](" + result["asset_url"] + ")")
    document = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    section = document.sections[-1]
    assert section.id == "posterior-visual-md"
    assert section.blocks[0].type == "asset"
    assert section.blocks[0].asset_url == result["asset_url"]
    assert executor.canvas_update_commands()[-1].section_id == "posterior-visual-md"


def test_generate_image_targets_existing_section_for_explicit_edit(tmp_path) -> None:
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
    written = setup.execute(
        "write",
        {
            "path": "/lecture/canvas/student/regression-tasks.md",
            "content": (
                "# Regression Tasks\n\n"
                "Regression maps inputs to continuous targets.\n\n"
                "Learning checkpoint: name the input, target, and loss."
            ),
        },
    )
    section_id = written["section_id"]
    before = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
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
            "prompt": "Visualize regression as data, model, loss, and prediction.",
            "section_id": section_id,
            "filename": "regression-visual",
        },
    )

    assert result["ok"] is True
    assert result["needs_canvas_edit"] is True
    assert result["target_path"] == written["path"]
    assert "Use edit, not write" in executor.pending_canvas_edit_instruction()
    after_generate = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    assert [section.id for section in after_generate.sections] == [section.id for section in before.sections]
    assert all(section.title != "Generated infographic" for section in after_generate.sections)

    edit = executor.execute(
        "edit",
        {
            "path": written["path"],
            "old_text": "Regression maps inputs to continuous targets.",
            "new_text": "Regression maps inputs to continuous targets.\n\n" + result["markdown"],
        },
    )

    assert edit["ok"] is True
    assert executor.pending_canvas_edit_instruction() is None
    document = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    section = next(section for section in document.sections if section.id == section_id)
    assert section.blocks[1].type == "asset"
    assert section.blocks[1].asset_url == result["asset_url"]


def test_pending_image_requires_edit_and_dedupes_insert(tmp_path) -> None:
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
    written = setup.execute(
        "write",
        {
            "path": "/lecture/canvas/student/prior-explanation.md",
            "content": "# Prior Explanation\n\nThe prior is the baseline before evidence.",
        },
    )
    executor = AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u1",
        image_generator=_FakeImageGenerator(),
    )
    image = executor.execute(
        "generate_image",
        {
            "prompt": "Show prior, likelihood, evidence, and posterior.",
            "section_id": written["section_id"],
            "filename": "bayes-prior",
        },
    )

    denied = executor.execute(
        "write",
        {
            "path": written["path"],
            "content": "# Prior Explanation\n\n" + image["markdown"],
        },
    )

    assert denied["ok"] is False
    assert "Use edit, not write" in denied["error"]
    edit = executor.execute(
        "edit",
        {
            "path": written["path"],
            "old_text": "The prior is the baseline before evidence.",
            "new_text": (
                "The prior is the baseline before evidence.\n\n"
                + image["markdown"]
                + "\n\nUse it as the bridge into Bayes' rule.\n\n"
                + image["markdown"]
            ),
        },
    )

    assert edit["ok"] is True
    assert executor.pending_canvas_edit_instruction() is None
    raw = (workspace.layout.user_canvas_dir("u1", "martius-ml", "lecture-03") / "student" / "90-prior-explanation.md").read_text()
    assert raw.count(image["asset_url"]) == 1
    assert raw.index("Use it as the bridge") < raw.index(image["asset_url"])


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
