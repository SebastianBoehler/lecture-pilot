from __future__ import annotations

from pathlib import Path

from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability
from lecturepilot.workspace_fs import WorkspaceFS, WorkspaceFSError


def safe_files(root: Path, *, suffix: str | None = None) -> list[Path]:
    if not root.exists():
        return []
    workspace = WorkspaceFS(WorkspaceCapability((CapabilityRoot("/root", root, writable=False),)))
    return [
        item.path
        for item in workspace.files("/root")
        if suffix is None or item.path.suffix.lower() == suffix
    ]


def safe_path(root: Path, path: Path) -> Path | None:
    if not root.exists():
        return None
    try:
        relative = path.relative_to(root)
    except ValueError:
        return None
    workspace = WorkspaceFS(WorkspaceCapability((CapabilityRoot("/root", root, writable=False),)))
    try:
        candidate = workspace.resolve(f"/root/{relative.as_posix()}").path
    except WorkspaceFSError:
        return None
    return candidate if candidate.is_file() else None
