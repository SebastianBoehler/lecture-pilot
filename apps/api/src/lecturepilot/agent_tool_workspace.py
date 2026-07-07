from __future__ import annotations

from pathlib import Path

from lecturepilot.agent_tool_utils import ToolPath, normalize_logical_path
from lecturepilot.canvas_workspace import CanvasWorkspace

WRITE_PREFIXES = (
    "/lecture/canvas/student/",
    "/lecture/canvas/components/",
    "/lecture/canvas/student-assets/",
    "/user/memories/",
    "/user/course/memories/",
)


def root_map(canvas_workspace: CanvasWorkspace, user_id: str, course_id: str, lecture_id: str) -> dict[str, Path]:
    layout = canvas_workspace.layout
    return {
        "/lecture/canvas": layout.user_canvas_dir(user_id, course_id, lecture_id),
        "/user/memories": layout.user_memories_dir(user_id),
        "/user/course/memories": layout.user_course_memories_dir(user_id, course_id),
        "/user/profile.json": layout.user_root(user_id) / "profile.json",
        "/course/canvas": layout.course_canvas_dir(course_id, lecture_id),
        "/course/source/uploads": layout.course_uploads_dir(course_id),
        "/course/materials": canvas_workspace.material_root,
    }


def resolve_path(logical_path: str, roots: dict[str, Path], *, for_write: bool = False) -> ToolPath:
    normalized = normalize_logical_path(logical_path)
    if for_write and not any(normalized.startswith(prefix) for prefix in WRITE_PREFIXES):
        raise ValueError("This path is read-only for the tutor agent.")
    for prefix, root in roots.items():
        if normalized == prefix or normalized.startswith(f"{prefix}/"):
            relative = normalized.removeprefix(prefix).lstrip("/")
            target = (root / relative).resolve()
            try:
                target.relative_to(root.resolve())
            except ValueError as exc:
                raise ValueError("Resolved path escapes the workspace root.") from exc
            return ToolPath(normalized, target)
    raise ValueError(f"Path is outside the agent workspace: {logical_path}")


def logical_for_path(path: Path, roots: dict[str, Path]) -> str:
    resolved = path.resolve()
    sorted_roots = sorted(roots.items(), key=lambda item: len(str(item[1])), reverse=True)
    for prefix, root in sorted_roots:
        try:
            return f"{prefix}/{resolved.relative_to(root.resolve())}".rstrip("/")
        except ValueError:
            continue
    return "/"
