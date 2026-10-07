from pathlib import Path

from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.canvas_workspace import CanvasWorkspace
from source_capability_test_helpers import published_source_workspace


def _executor(workspace):
    return AgentToolExecutor(
        canvas_workspace=workspace,
        course_id="course-a",
        lecture_id="lecture-open",
        user_id="student",
    )


def test_hidden_learning_map_is_denied_by_every_read_tool(tmp_path):
    workspace = CanvasWorkspace(workspace_root=tmp_path, material_root=tmp_path / "material")
    root = workspace.layout.course_canvas_dir("course-a", "lecture-open")
    root.mkdir(parents=True)
    (root / "learning-map.json").write_text('{"secret": "Hidden transfer prompt"}')
    (root / "index.md").write_text("Published teaching")
    executor = _executor(workspace)
    assert not executor.execute("read", {"path": "/course/canvas/learning-map.json"})["ok"]
    for tool, args in (("ls", {}), ("find", {}), ("grep", {"pattern": "Hidden"})):
        result = executor.execute(tool, {"path": "/course/canvas", **args})
        assert result["ok"]
        assert "learning-map.json" not in str(result)
        assert "Hidden transfer prompt" not in str(result)


def test_source_tools_only_expose_the_current_lecture_manifest(tmp_path):
    workspace = published_source_workspace(tmp_path)
    executor = _executor(workspace)
    assert executor.execute("read", {"path": "/course/source/uploads/current.md"})["ok"]
    for name in ("future.md", "unassigned.md", "course-wide.md"):
        assert not executor.execute("read", {"path": f"/course/source/uploads/{name}"})["ok"]
    for tool, args in (("ls", {}), ("find", {}), ("grep", {"pattern": "secret"})):
        result = executor.execute(tool, {"path": "/course/source/uploads", **args})
        assert result["ok"]
        assert "current.md" in str(result)
        assert "future.md" not in str(result)
        assert "unassigned.md" not in str(result)
        assert "course-wide.md" not in str(result)


def test_missing_manifest_never_grants_course_wide_source_access(tmp_path):
    workspace = CanvasWorkspace(workspace_root=tmp_path, material_root=tmp_path / "material")
    root = workspace.layout.course_uploads_dir("course-a")
    root.mkdir(parents=True)
    (root / "future.md").write_text("Future teaching")
    executor = _executor(workspace)
    assert not executor.execute("read", {"path": "/course/source/uploads/future.md"})["ok"]
    assert not executor.execute("find", {"path": "/course/source/uploads"})["ok"]


def test_file_tools_cannot_bypass_remember_consent_or_profile_validation(tmp_path):
    executor = _executor(CanvasWorkspace(workspace_root=tmp_path, material_root=tmp_path))
    for path in ("/user/memories/preferences.json", "/user/course/memories/course.md"):
        assert not executor.execute("write", {"path": path, "content": "bypass"})["ok"]


def test_tutor_roots_do_not_expose_global_material_root(tmp_path: Path) -> None:
    material_root = tmp_path / "private-material"
    material_root.mkdir()
    (material_root / "future-lecture.md").write_text("not unlocked", encoding="utf-8")
    executor = AgentToolExecutor(
        canvas_workspace=CanvasWorkspace(
            workspace_root=tmp_path / "workspaces",
            material_root=material_root,
        ),
        course_id="martius-ml",
        lecture_id="lecture-03",
        user_id="student01",
    )

    roots = executor.execute("pwd", {})
    denied = executor.execute("read", {"path": "/course/materials/future-lecture.md"})

    assert "/course/materials" not in roots["roots"]
    assert denied == {
        "ok": False,
        "error": "Path is outside the workspace capability.",
    }


def test_private_assessment_audit_is_outside_tutor_roots(tmp_path):
    workspace = CanvasWorkspace(workspace_root=tmp_path, material_root=tmp_path)
    root = workspace.layout.user_canvas_dir("student", "course-a", "lecture-open").parent
    root.mkdir(parents=True, exist_ok=True)
    (root / "assessment-audit.jsonl").write_text('"private answer quotation"')
    executor = _executor(workspace)
    assert not executor.execute("read", {"path": "/lecture/assessment-audit.jsonl"})["ok"]
    assert "private answer quotation" not in str(executor.execute("pwd", {}))
