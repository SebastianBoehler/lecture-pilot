from __future__ import annotations

import json
from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.latex_canvas_text import slug


def asset_section(
    path: str,
    source_root: Path,
    course_id: str,
    lecture_id: str,
) -> CanvasSection:
    section_id = slug(f"asset {path}")
    caption = media_caption(source_root, path)
    return CanvasSection(
        id=section_id,
        title=media_title(path, caption),
        source_ref=path,
        blocks=[
            CanvasBlock(
                id=f"{section_id}-asset-1",
                type="asset",
                asset_path=path,
                asset_url=f"/course-assets/{course_id}/{lecture_id}/{path}",
                caption=caption,
            )
        ],
    )


def video_section(
    path: str,
    source_root: Path,
    course_id: str,
    lecture_id: str,
) -> CanvasSection:
    section_id = slug(f"video {path}")
    caption = media_caption(source_root, path)
    return CanvasSection(
        id=section_id,
        title=media_title(path, caption),
        source_ref=path,
        blocks=[
            CanvasBlock(
                id=f"{section_id}-video-1",
                type="video",
                asset_path=path,
                asset_url=f"/course-assets/{course_id}/{lecture_id}/{path}",
                caption=caption,
            )
        ],
    )


def media_caption(source_root: Path, path: str) -> str:
    metadata = _metadata(source_root / path)
    if metadata:
        title = _metadata_value(metadata, "title", "caption", "alt") or _filename_title(path)
        details = _metadata_value(metadata, "description", "summary")
        tags = metadata.get("tags")
        tag_text = (
            ", ".join(str(tag).strip() for tag in tags[:8] if str(tag).strip())
            if isinstance(tags, list)
            else ""
        )
        return " - ".join(part for part in [title, details, tag_text] if part)[:500]
    return _filename_title(path)[:500]


def media_title(path: str, caption: str) -> str:
    return (caption.split(" - ", 1)[0] or _filename_title(path))[:200]


def _metadata(path: Path) -> dict | None:
    for candidate in (path.with_suffix(path.suffix + ".json"), path.with_suffix(".json")):
        if candidate.exists() and candidate.stat().st_size <= 32_000:
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            if isinstance(payload, dict):
                return payload
    return None


def _metadata_value(metadata: dict, *keys: str) -> str:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _filename_title(path: str) -> str:
    return Path(path).stem.replace("-", " ").replace("_", " ").title()
