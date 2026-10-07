from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.canvas_workspace import CanvasWorkspace


def test_grep_returns_an_error_for_catastrophic_or_invalid_patterns(tmp_path):
    workspace = CanvasWorkspace(workspace_root=tmp_path, material_root=tmp_path)
    root = workspace.layout.course_canvas_dir("course", "lecture")
    root.mkdir(parents=True)
    (root / "index.md").write_text("a" * 20000 + "!")
    executor = AgentToolExecutor(
        canvas_workspace=workspace, course_id="course", lecture_id="lecture", user_id="student"
    )
    for pattern, error in (("(a+)+$", "time limit"), ("[", "Invalid search")):
        result = executor.execute("grep", {"path": "/course/canvas", "pattern": pattern})
        assert result["ok"] is False
        assert error in result["error"]
