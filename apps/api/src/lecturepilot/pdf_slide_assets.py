from __future__ import annotations

from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.storage_layout import safe_id


# Bound CPU, memory, and disk work for a single draft on small self-hosted instances.
MAX_RENDERED_SLIDES = 20


class PdfSlideAssetError(RuntimeError):
    """Raised when original slide images cannot be rendered."""


def render_pdf_slide_blocks(
    *,
    pdf_path: Path,
    source_root: Path,
    output_root: Path | None = None,
    course_id: str,
    lecture_id: str,
    source_ref: str,
) -> list[CanvasBlock]:
    if pdf_path.suffix.lower() != ".pdf":
        raise PdfSlideAssetError("Only PDF source files can be rendered as slides.")

    fitz = _fitz()
    stem = safe_id(pdf_path.stem)
    slide_root = f"generated-slides/{safe_id(lecture_id)}/{stem}"
    output_root = output_root or source_root
    (output_root / slide_root).mkdir(parents=True, exist_ok=True)
    try:
        document = fitz.open(pdf_path)
        try:
            return [
                _render_page(
                    document=document,
                    fitz=fitz,
                    output_root=output_root,
                    slide_root=slide_root,
                    course_id=course_id,
                    lecture_id=lecture_id,
                    source_ref=source_ref,
                    index=index,
                )
                for index in range(min(len(document), MAX_RENDERED_SLIDES))
            ]
        finally:
            document.close()
    except Exception as exc:
        raise PdfSlideAssetError(f"Could not render PDF source {pdf_path.name}.") from exc


def _render_page(
    *,
    document,
    fitz,
    output_root: Path,
    slide_root: str,
    course_id: str,
    lecture_id: str,
    source_ref: str,
    index: int,
) -> CanvasBlock:
    number = index + 1
    asset_path = f"{slide_root}/slide-{number:03}.png"
    output_path = output_root / asset_path
    if not output_path.exists():
        pixmap = document.load_page(index).get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        pixmap.save(output_path)
    return CanvasBlock(
        id=f"{safe_id(lecture_id)}-original-slide-{number:03}",
        type="asset",
        asset_path=asset_path,
        asset_url=f"/course-assets/{course_id}/{lecture_id}/{asset_path}",
        caption=f"Original slide {number} from {source_ref}",
    )


def _fitz():
    try:
        import fitz
    except ImportError as exc:
        raise PdfSlideAssetError("PyMuPDF is required to render original slides.") from exc
    return fitz
