from __future__ import annotations

from pathlib import PurePosixPath

from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.latex_canvas_text import BROWSER_ASSET_SUFFIXES

_COURSE_ASSET_SUFFIXES = BROWSER_ASSET_SUFFIXES | {
    ".avi",
    ".mkv",
    ".mov",
    ".mp4",
    ".webm",
}


def asset_markdown_target(block: CanvasBlock) -> str:
    if block.asset_url and block.asset_url.startswith("/workspace-assets/"):
        return block.asset_url
    if block.asset_url and block.asset_url.startswith(("http://", "https://")):
        return block.asset_url
    target = block.asset_path or block.asset_url or ""
    local_path = target.removeprefix("asset:")
    if not _is_safe_local_asset_path(local_path):
        return ""
    return f"asset:{target}" if not target.startswith("asset:") else target


def parsed_asset_target(
    target: str,
    *,
    course_id: str,
    lecture_id: str,
) -> tuple[str | None, str]:
    if target.startswith(("http://", "https://")):
        return None, target
    if target.startswith("/workspace-assets/"):
        asset_path = _workspace_asset_path(target)
        if not _is_safe_local_asset_path(asset_path):
            return None, ""
        return asset_path, target
    if "/lecture/canvas/student-assets/" in target:
        relative = target.split("/lecture/canvas/student-assets/", 1)[1]
        asset_path = f"student-assets/{relative}"
        if not _is_safe_local_asset_path(asset_path):
            return None, ""
        return asset_path, target
    asset_path = target.removeprefix("asset:").strip()
    if not _is_safe_local_asset_path(asset_path):
        return None, ""
    return asset_path, f"/course-assets/{course_id}/{lecture_id}/{asset_path}"


def _workspace_asset_path(target: str) -> str:
    if "/student-assets/" not in target:
        return target.rsplit("/", 1)[-1]
    return f"student-assets/{target.split('/student-assets/', 1)[1]}"


def _is_safe_local_asset_path(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(
        value
        and not value.startswith("/")
        and ".." not in path.parts
        and path.suffix.lower() in _COURSE_ASSET_SUFFIXES
    )
