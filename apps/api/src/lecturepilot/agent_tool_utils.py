from __future__ import annotations

from pathlib import Path, PurePosixPath
from dataclasses import dataclass
from typing import Any

_TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".tex", ".csv", ".py"}


class AgentToolArgumentError(RuntimeError):
    """Raised when a model supplied invalid tool arguments."""


@dataclass(frozen=True)
class ToolPath:
    logical: str
    path: Path


def file_entry(logical: str, path: Path) -> dict[str, Any]:
    return {
        "path": logical,
        "type": "dir" if path.is_dir() else "file",
        "bytes": path.stat().st_size if path.is_file() else None,
    }


def normalize_logical_path(path: str) -> str:
    normalized = PurePosixPath(path if path.startswith("/") else f"/{path}")
    hidden = any(part.startswith(".") for part in normalized.parts if part != "/")
    if ".." in normalized.parts or hidden:
        raise AgentToolArgumentError("Unsafe workspace path.")
    return str(normalized)


def relative_write_path(logical: str) -> str:
    return (
        logical.removeprefix("/lecture/canvas/")
        .removeprefix("/user/memories/")
        .removeprefix("/user/course/memories/")
    )


def require_current_canvas_write_path(logical_path: str) -> None:
    if not logical_path.startswith("/lecture/canvas/"):
        return
    if logical_path.startswith(("/lecture/canvas/student/", "/lecture/canvas/student-assets/")):
        return
    raise AgentToolArgumentError("This workspace root is read-only.")


def resolve_tool_path(workspace_fs: Any, logical_path: str, *, for_write: bool) -> ToolPath:
    try:
        if for_write:
            require_current_canvas_write_path(logical_path)
        return workspace_fs.resolve(logical_path, for_write=for_write)
    except ValueError as exc:
        raise AgentToolArgumentError(str(exc)) from exc


def required_str(args: dict[str, Any], name: str, default: str | None = None) -> str:
    value = args.get(name, default)
    if not isinstance(value, str) or (default is None and not value.strip()):
        raise AgentToolArgumentError(f"Tool argument {name} must be a non-empty string.")
    return value


def int_arg(args: dict[str, Any], name: str, default: int) -> int:
    value = args.get(name, default)
    return value if isinstance(value, int) else default


def is_text_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in _TEXT_SUFFIXES
