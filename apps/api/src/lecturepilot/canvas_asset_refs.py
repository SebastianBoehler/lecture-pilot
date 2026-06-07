from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock


def asset_markdown_target(block: CanvasBlock) -> str:
    if block.asset_url and block.asset_url.startswith("/workspace-assets/"):
        return block.asset_url
    target = block.asset_path or block.asset_url or ""
    return f"asset:{target}" if not target.startswith("asset:") else target


def parsed_asset_target(
    target: str,
    *,
    course_id: str,
    lecture_id: str,
) -> tuple[str, str]:
    if target.startswith("/workspace-assets/"):
        asset_path = _workspace_asset_path(target)
        return asset_path, target
    asset_path = target.removeprefix("asset:")
    return asset_path, f"/course-assets/{course_id}/{lecture_id}/{asset_path}"


def _workspace_asset_path(target: str) -> str:
    if "/student-assets/" not in target:
        return target.rsplit("/", 1)[-1]
    return f"student-assets/{target.split('/student-assets/', 1)[1]}"
