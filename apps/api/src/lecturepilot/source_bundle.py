from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceBundleFile:
    path: str
    kind: str
    size_bytes: int


def scan_source_bundle(root: Path) -> list[SourceBundleFile]:
    files = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
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
    return path.parts[:1] == ("canvas",) or any(part.startswith(".") for part in path.parts)
