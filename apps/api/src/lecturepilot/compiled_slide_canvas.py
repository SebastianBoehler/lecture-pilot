from __future__ import annotations

import re
from pathlib import Path

from lecturepilot.canvas_models import CanvasSection
from lecturepilot.pdf_slide_assets import PdfSlideAssetError, render_pdf_slide_blocks


def compiled_slide_preview(
    *,
    pdf_path: Path,
    output_root: Path,
    course_id: str,
    lecture_id: str,
    source_ref: str,
) -> tuple[CanvasSection | None, str | None]:
    try:
        blocks = render_pdf_slide_blocks(
            pdf_path=pdf_path,
            source_root=output_root,
            output_root=output_root,
            course_id=course_id,
            lecture_id=lecture_id,
            source_ref=source_ref,
            caption_kind="compiled",
        )
    except PdfSlideAssetError:
        return None, latex_preview_warning(lecture_id, source_ref)
    if not blocks:
        return None, latex_preview_warning(lecture_id, source_ref)
    return (
        CanvasSection(
            id="compiled-original-slide-assets",
            title="Compiled slide previews",
            source_ref=f"{source_ref} compiled preview",
            blocks=blocks,
        ),
        None,
    )


def latex_preview_warning(lecture_id: str, source_ref: str) -> str:
    match = re.search(r"(\d{1,3})$", lecture_id)
    label = f"Lecture {int(match.group(1)):02d}" if match else lecture_id
    return (
        f"{label} · {source_ref}: Original slide previews could not be created from LaTeX. "
        "The text canvas is ready. Upload a matching PDF or fix the LaTeX source, then "
        "regenerate."
    )
