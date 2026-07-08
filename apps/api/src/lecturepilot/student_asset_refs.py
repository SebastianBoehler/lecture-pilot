from __future__ import annotations

from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument
from lecturepilot.storage_layout import StorageLayout, safe_id


def resolve_student_asset_refs(
    document: CanvasDocument,
    *,
    asset_url_prefix: str | None = None,
    canvas_dir: Path,
    course_id: str,
    lecture_id: str,
    layout: StorageLayout,
    user_id: str,
) -> CanvasDocument:
    prefix = asset_url_prefix or (
        f"/workspace-assets/{safe_id(course_id)}/{safe_id(lecture_id)}/"
        f"{layout.user_key(user_id)}/student-assets"
    )
    sections = [
        section.model_copy(update={"blocks": [
            _resolve_student_asset_block(block, canvas_dir=canvas_dir, asset_url_prefix=prefix)
            for block in section.blocks
        ]})
        for section in document.sections
    ]
    return document.model_copy(update={"sections": sections})


def _resolve_student_asset_block(
    block: CanvasBlock,
    *,
    canvas_dir: Path,
    asset_url_prefix: str,
) -> CanvasBlock:
    if block.type != "asset":
        return block
    target = _student_asset_target(block.asset_path, block.asset_url)
    if not target:
        return block
    relative = Path(target)
    if relative.is_absolute() or ".." in relative.parts:
        return block
    if not (canvas_dir / "student-assets" / relative).exists():
        return block
    asset_path = f"student-assets/{relative.as_posix()}"
    return block.model_copy(update={
        "asset_path": asset_path,
        "asset_url": f"{asset_url_prefix}/{relative.as_posix()}",
    })


def _student_asset_target(asset_path: str | None, asset_url: str | None) -> str | None:
    for value in (asset_path, asset_url):
        if not value:
            continue
        if value.startswith("student-assets/"):
            return value.removeprefix("student-assets/")
        marker = "/lecture/canvas/student-assets/"
        if marker in value:
            return value.split(marker, 1)[1]
    return None
