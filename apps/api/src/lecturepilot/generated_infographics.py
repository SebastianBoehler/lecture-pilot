from __future__ import annotations

import re
from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.image_generation import ImageGenerationError, ImageGenerator


def materialize_infographic_sections(
    *,
    sections: list[CanvasSection],
    prompt: str,
    asset_dir: Path,
    asset_url_prefix: str,
    image_generator: ImageGenerator | None = None,
) -> list[CanvasSection]:
    if not _asks_for_image(prompt):
        return sections
    needs_image = [_is_student_section(section) and not _has_asset(section) for section in sections]
    if any(needs_image) and image_generator is None:
        raise ImageGenerationError(
            "Infographic generation requires a configured text-to-image provider."
        )
    asset_dir.mkdir(parents=True, exist_ok=True)
    return [
        _with_infographic(
            section,
            prompt=prompt,
            asset_dir=asset_dir,
            asset_url_prefix=asset_url_prefix,
            image_generator=image_generator,
        )
        if _is_student_section(section) and not _has_asset(section)
        else section
        for section in sections
    ]


def _with_infographic(
    section: CanvasSection,
    *,
    prompt: str,
    asset_dir: Path,
    asset_url_prefix: str,
    image_generator: ImageGenerator | None,
) -> CanvasSection:
    asset_dir.mkdir(parents=True, exist_ok=True)
    if image_generator is None:
        raise ImageGenerationError(
            "Infographic generation requires a configured text-to-image provider."
        )
    generated = image_generator.generate_infographic(prompt=prompt, section=section)
    if generated.extension == "svg":
        raise ImageGenerationError("Image providers must return a raster image for infographics.")
    filename = f"{_safe_slug(section.id)}.{generated.extension}"
    (asset_dir / filename).write_bytes(generated.content)
    caption = generated.caption
    asset_path = f"student-assets/{filename}"
    asset = CanvasBlock(
        id=f"{section.id}-infographic",
        type="asset",
        asset_path=asset_path,
        asset_url=f"{asset_url_prefix}/{filename}",
        caption=caption,
    )
    return section.model_copy(update={"blocks": [asset, *section.blocks]})


def _asks_for_image(prompt: str) -> bool:
    normalized = prompt.lower()
    return any(word in normalized for word in ("infographic", "diagram", "image", "visual"))


def _is_student_section(section: CanvasSection) -> bool:
    return section.source_ref == "student workspace" or section.id.startswith("student-")


def _has_asset(section: CanvasSection) -> bool:
    return any(block.type == "asset" for block in section.blocks)


def _safe_slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")[:96] or "infographic"
