from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from lecturepilot.tenancy import tenant_storage_prefix


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
        ".jsonl": ("jsonl", 2 * 1024 * 1024),
        ".yaml": ("yaml", 2 * 1024 * 1024),
        ".yml": ("yaml", 2 * 1024 * 1024),
        ".png": ("image", 20 * 1024 * 1024),
        ".jpg": ("image", 20 * 1024 * 1024),
        ".jpeg": ("image", 20 * 1024 * 1024),
        ".webp": ("image", 20 * 1024 * 1024),
        ".svg": ("svg", 2 * 1024 * 1024),
    }
    allowed_course_material_uploads: dict[str, tuple[str, int]] = {
        ".tex": ("latex", 10 * 1024 * 1024),
        ".sty": ("latex-support", 10 * 1024 * 1024),
        ".cls": ("latex-support", 10 * 1024 * 1024),
        ".bib": ("latex-support", 10 * 1024 * 1024),
        ".bst": ("latex-support", 10 * 1024 * 1024),
        ".md": ("markdown", 5 * 1024 * 1024),
        ".txt": ("text", 2 * 1024 * 1024),
        ".csv": ("table", 5 * 1024 * 1024),
        ".json": ("json", 2 * 1024 * 1024),
        ".pdf": ("pdf", 100 * 1024 * 1024),
        ".png": ("image", 20 * 1024 * 1024),
        ".jpg": ("image", 20 * 1024 * 1024),
        ".jpeg": ("image", 20 * 1024 * 1024),
        ".webp": ("image", 20 * 1024 * 1024),
        ".gif": ("image", 20 * 1024 * 1024),
        ".svg": ("svg", 2 * 1024 * 1024),
        ".mp4": ("video", 500 * 1024 * 1024),
        ".webm": ("video", 500 * 1024 * 1024),
        ".mov": ("video", 500 * 1024 * 1024),
        ".mkv": ("video", 500 * 1024 * 1024),
        ".avi": ("video", 500 * 1024 * 1024),
        ".py": ("code", 5 * 1024 * 1024),
        ".ipynb": ("notebook", 20 * 1024 * 1024),
    }

    def validate_write(self, path: str, size_bytes: int) -> CheckedWorkspaceFile:
        return self._validate_file(path, size_bytes, allowed=self.allowed_writes)

    def validate_course_material_upload(
        self,
        *,
        tenant_id: str,
        path: str,
        size_bytes: int,
    ) -> CheckedWorkspaceFile:
        checked = self._validate_file(
            path,
            size_bytes,
            allowed=self.allowed_course_material_uploads,
        )
        storage_path = f"{tenant_storage_prefix(tenant_id)}/course-materials/{checked.path}"
        return CheckedWorkspaceFile(storage_path, checked.kind, checked.max_bytes)

    def _validate_file(
        self,
        path: str,
        size_bytes: int,
        *,
        allowed: dict[str, tuple[str, int]],
    ) -> CheckedWorkspaceFile:
        normalized = PurePosixPath(path)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise WorkspacePolicyError("Workspace paths must stay inside the workspace.")
        if not normalized.parts or any(part.startswith(".") for part in normalized.parts):
            raise WorkspacePolicyError("Hidden workspace paths are not allowed.")
        suffix = normalized.suffix.lower()
        if suffix not in allowed:
            raise WorkspacePolicyError(f"File type {suffix or '<none>'} is not writable.")
        kind, max_bytes = allowed[suffix]
        if size_bytes > max_bytes:
            raise WorkspacePolicyError(f"{suffix} files are limited to {max_bytes} bytes.")
        return CheckedWorkspaceFile(str(normalized), kind, max_bytes)
