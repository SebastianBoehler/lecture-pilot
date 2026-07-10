from __future__ import annotations

from pathlib import Path

from lecturepilot.canvas_models import CanvasSection
from lecturepilot.pdf_slide_assets import PdfSlideAssetError, render_pdf_slide_blocks


def append_matching_pdf_slides(
    *,
    sections: list[CanvasSection],
    source_path: Path,
    material_root: Path,
    course_id: str,
    lecture_id: str,
    derived_root: Path | None = None,
) -> list[CanvasSection]:
    pdf_path = source_path.with_suffix(".pdf")
    if not pdf_path.exists():
        return sections
    try:
        slides = render_pdf_slide_blocks(
            pdf_path=pdf_path,
            source_root=material_root,
            output_root=derived_root,
            course_id=course_id,
            lecture_id=lecture_id,
            source_ref=pdf_path.name,
        )
    except PdfSlideAssetError:
        return sections
    if not slides:
        return sections
    slide_section = CanvasSection(
        id="original-slide-assets",
        title="Original slide assets",
        source_ref=pdf_path.name,
        blocks=slides,
    )
    return [*sections, slide_section]
