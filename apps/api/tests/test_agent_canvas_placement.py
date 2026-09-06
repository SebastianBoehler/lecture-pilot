from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.canvas_markdown import read_section_frontmatter
from test_canvas_api import _workspace


def test_contextual_insert_preserves_order_on_reload_and_rewrite(tmp_path):
    workspace = _workspace(tmp_path)
    document = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u")
    anchor = document.sections[0].id
    executor = AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u",
        initial_focus_section_id=anchor,
    )

    def write(name, content):
        return executor.execute(
            "write", {"path": f"/lecture/canvas/student/{name}.md", "content": content}
        )

    result = write("explanation", "# Explanation\n\nA concrete example.")
    assert result["ok"], result
    second = write("another", "# Another\n\nAnother example.")
    assert second["ok"], second
    saved = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u")
    assert [s.id for s in saved.sections][:3] == [
        anchor,
        result["section_id"],
        second["section_id"],
    ]
    commands = executor.canvas_update_commands()
    assert commands[0].placement.section_id == anchor
    assert commands[1].placement.section_id == result["section_id"]
    executor.initial_focus_section_id = second["section_id"]
    rewritten = write("explanation", "# Explanation\n\nRevised example.")
    assert rewritten["ok"], rewritten
    path = executor.workspace_fs.resolve(rewritten["path"]).path
    assert read_section_frontmatter(path)["placement_section_id"] == anchor


def test_explicit_placement_rejects_unknown_anchor_and_supports_before(tmp_path):
    workspace = _workspace(tmp_path)
    document = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u")
    executor = AgentToolExecutor(
        canvas_workspace=workspace, course_id="martius-ml", lecture_id="lecture-03", user_id="u"
    )

    def write(anchor):
        return executor.execute(
            "write",
            {
                "path": "/lecture/canvas/student/intro.md",
                "content": f'---\nid: "intro"\ntitle: "Intro"\nsource_ref: "student workspace"\n'
                f'placement_mode: "before_section"\nplacement_section_id: "{anchor}"\n---\n\nAn example.',
            },
        )

    assert write("missing")["ok"] is False
    assert write("intro")["ok"] is False
    assert write(document.sections[0].id)["ok"] is True
    saved = workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u")
    assert saved.sections[0].id == "intro"
    assert executor.canvas_update_commands()[0].placement.mode == "before_section"
