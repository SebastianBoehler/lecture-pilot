from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath


class WorkspacePolicyError(ValueError):
    """Raised when a workspace path or file payload violates policy."""


@dataclass(frozen=True)
class CheckedWorkspaceFile:
    path: str
    kind: str
    max_bytes: int


class WorkspacePolicy:
    """Typed file policy for self-hostable learner workspaces."""

    allowed_writes: dict[str, tuple[str, int]] = {
        ".md": ("markdown", 5 * 1024 * 1024),
        ".txt": ("text", 2 * 1024 * 1024),
        ".json": ("json", 2 * 1024 * 1024),
        ".png": ("image", 20 * 1024 * 1024),
        ".svg": ("svg", 2 * 1024 * 1024),
    }

    def validate_write(self, path: str, size_bytes: int) -> CheckedWorkspaceFile:
        normalized = PurePosixPath(path)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise WorkspacePolicyError("Workspace paths must stay inside the workspace.")
        if not normalized.parts or any(part.startswith(".") for part in normalized.parts):
            raise WorkspacePolicyError("Hidden workspace paths are not allowed.")
        suffix = normalized.suffix.lower()
        if suffix not in self.allowed_writes:
            raise WorkspacePolicyError(f"File type {suffix or '<none>'} is not writable.")
        kind, max_bytes = self.allowed_writes[suffix]
        if size_bytes > max_bytes:
            raise WorkspacePolicyError(f"{suffix} files are limited to {max_bytes} bytes.")
        return CheckedWorkspaceFile(str(normalized), kind, max_bytes)

