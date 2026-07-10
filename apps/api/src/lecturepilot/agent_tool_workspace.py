from __future__ import annotations

from pathlib import Path

from lecturepilot.agent_tool_utils import ToolPath
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.workspace_capability import learner_workspace_capability
from lecturepilot.workspace_fs import WorkspaceFS


def root_map(
    canvas_workspace: CanvasWorkspace, user_id: str, course_id: str, lecture_id: str
) -> dict[str, Path]:
    capability = learner_workspace_capability(
        canvas_workspace, user_id=user_id, course_id=course_id, lecture_id=lecture_id
    )
    return {root.logical_path: root.host_path for root in capability.roots}


def resolve_path(logical_path: str, roots: dict[str, Path], *, for_write: bool = False) -> ToolPath:
    from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability

    writable = {"/lecture/canvas", "/user/memories", "/user/course/memories"}
    capability = WorkspaceCapability(
        tuple(CapabilityRoot(prefix, path, prefix in writable) for prefix, path in roots.items())
    )
    return WorkspaceFS(capability).resolve(logical_path, for_write=for_write)


def logical_for_path(path: Path, roots: dict[str, Path]) -> str:
    from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability

    capability = WorkspaceCapability(
        tuple(CapabilityRoot(prefix, root) for prefix, root in roots.items())
    )
    return WorkspaceFS(capability).logical_for(path)
