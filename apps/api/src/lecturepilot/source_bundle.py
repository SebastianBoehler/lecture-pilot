from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lecturepilot.workspace_capability import CapabilityRoot, WorkspaceCapability
from lecturepilot.workspace_fs import WorkspaceFS


@dataclass(frozen=True)
class SourceBundleFile:
    path: str
    kind: str
    size_bytes: int


def scan_source_bundle(root: Path) -> list[SourceBundleFile]:
    if not root.exists():
        return []
    workspace = WorkspaceFS(
        WorkspaceCapability((CapabilityRoot("/source", root, writable=False),))
    )
    files = []
    for item in sorted(workspace.files("/source"), key=lambda item: item.logical):
        path = item.path
        if _is_hidden(path.relative_to(root)) or ".lecturepilot-previews" in path.parts:
            continue
        kind = SOURCE_SUFFIXES.get(path.suffix.lower())
        if kind:
            files.append(
                SourceBundleFile(
                    path=path.relative_to(root).as_posix(),
                    kind=kind,
                    size_bytes=path.stat().st_size,
                )
            )
    return files


SOURCE_SUFFIXES = {
    ".tex": "latex",
    ".sty": "latex-support",
    ".md": "markdown",
    ".txt": "text",
    ".csv": "table",
    ".json": "json",
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".gif": "image",
    ".svg": "svg",
    ".mp4": "video",
    ".webm": "video",
    ".mov": "video",
    ".mkv": "video",
    ".avi": "video",
    ".py": "code",
    ".ipynb": "notebook",
}


def _is_hidden(path: Path) -> bool:
    derived_roots = {"canvas", "generated-slides", "normalized"}
    return bool(path.parts[:1] and path.parts[0] in derived_roots) or any(
        part.startswith(".") for part in path.parts
    )
