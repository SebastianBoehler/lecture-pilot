from lecturepilot.agent_tool_executor import AgentToolExecutor
from test_canvas_api import _workspace


def test_unix_named_tools_search_read_and_write_canvas(tmp_path) -> None:
    workspace = _workspace(tmp_path)
    workspace.read_document(course_id="martius-ml", lecture_id="lecture-03", user_id="u1")
    executor = AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u1",
    )

    assert executor.execute("ls", {"path": "/"})["entries"]
    matches = executor.execute("grep", {"path": "/course/canvas", "pattern": "Bayes"})
    assert matches["ok"] is True
    assert matches["matches"]
    result = executor.execute(
        "write",
        {
            "path": "/lecture/canvas/student/loss-note.md",
            "content": (
                "---\n"
                'id: "student-loss-note"\n'
                'title: "Loss note"\n'
                'source_ref: "student workspace"\n'
                "---\n\n"
                '<!-- block id="student-loss-note-p-1" type="paragraph" -->\n'
                "Loss functions change which decision is rational.\n"
            ),
        },
    )

    assert result["ok"] is True
    assert result["path"] == "/lecture/canvas/student/90-loss-note.md"
    commands = executor.canvas_update_commands()
    assert commands[0].type == "update_section"
    assert commands[0].section_id == "student-loss-note"
    plain = executor.execute(
        "write",
        {
            "path": "/lecture/canvas/student/plain-threshold-note.md",
            "content": "# Plain threshold note\n\nLoss thresholds shift the rational decision boundary.",
        },
    )
    assert plain["ok"] is True
    assert plain["path"] == "/lecture/canvas/student/91-plain-threshold-note.md"
    assert plain["section_id"] == "plain-threshold-note-md"
    section_ids = {command.section_id for command in executor.canvas_update_commands()}
    assert "plain-threshold-note-md" in section_ids
    plain_section = workspace.read_document(
        course_id="martius-ml", lecture_id="lecture-03", user_id="u1"
    ).sections[-1]
    assert plain_section.title == "Plain threshold note"
    assert "# Plain threshold note" not in plain_section.blocks[0].text
    assert executor.canvas_update_commands()[-1].section_id == "plain-threshold-note-md"
    highlighted = executor.execute(
        "highlight",
        {
            "span_id": "plain-threshold-note-md-paragraph-1",
            "highlight_text": "Loss thresholds shift the rational decision boundary.",
        },
    )
    assert highlighted["ok"] is True
    assert highlighted["span_id"] != "plain-threshold-note-md-paragraph-1"
    denied = executor.execute("write", {"path": "/course/materials/x.md", "content": "no"})
    assert denied == {"ok": False, "error": "Path is outside the workspace capability."}


def test_learner_tools_reject_external_canvas_authority_files(tmp_path) -> None:
    executor = AgentToolExecutor(
        canvas_workspace=_workspace(tmp_path),
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="u1",
    )

    component = executor.execute(
        "write",
        {
            "path": "/lecture/canvas/components/external.yaml",
            "content": "id: external\ntype: single_choice_quiz\n",
        },
    )
    placement = executor.execute(
        "write",
        {"path": "/lecture/canvas/placement.json", "content": "{}"},
    )

    assert (
        component
        == placement
        == {
            "ok": False,
            "error": "This workspace root is read-only.",
        }
    )
