from pathlib import Path

from lecturepilot.agent_tool_executor import AgentToolExecutor
from lecturepilot.canvas_workspace import CanvasWorkspace


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
