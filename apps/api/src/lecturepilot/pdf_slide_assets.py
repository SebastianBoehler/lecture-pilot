from __future__ import annotations

import hashlib
from pathlib import Path

from lecturepilot.bounded_processing import BoundedProcessingError, run_bounded
from lecturepilot.bounded_sampling import evenly_sampled_indexes
from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.storage_layout import safe_id


# Bound CPU, memory, and disk work for a single draft on small self-hosted instances.
MAX_RENDERED_SLIDES = 20
MAX_RENDERED_PIXELS = 20_000_000


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
    caption_kind: str = "original",
) -> list[CanvasBlock]:
    if pdf_path.suffix.lower() != ".pdf":
        raise PdfSlideAssetError("Only PDF source files can be rendered as slides.")
    if caption_kind not in {"original", "compiled"}:
        raise PdfSlideAssetError("PDF slide caption kind is invalid.")

    try:
        payloads = run_bounded(
            _render_pdf_payloads,
            str(pdf_path),
            str(output_root or source_root),
            course_id,
            lecture_id,
            source_ref,
            caption_kind,
        )
    except BoundedProcessingError as exc:
        raise PdfSlideAssetError(str(exc)) from exc
    except PdfSlideAssetError:
        raise
    except Exception as exc:
        raise PdfSlideAssetError(f"Could not render PDF source {pdf_path.name}.") from exc
    return [CanvasBlock.model_validate(payload) for payload in payloads]


def _render_pdf_payloads(
    pdf_path: str,
    output_root: str,
    course_id: str,
    lecture_id: str,
    source_ref: str,
    caption_kind: str,
) -> list[dict]:
    fitz = _fitz()
    pdf = Path(pdf_path)
    root = Path(output_root)
    stem = safe_id(pdf.stem)
    fingerprint = _pdf_fingerprint(pdf)
    slide_root = f"generated-slides/{safe_id(lecture_id)}/{stem}-{fingerprint}"
    (root / slide_root).mkdir(parents=True, exist_ok=True)
    document = fitz.open(pdf)
    try:
        return [
            _render_page(
                document=document,
                fitz=fitz,
                output_root=root,
                slide_root=slide_root,
                course_id=course_id,
                lecture_id=lecture_id,
                source_ref=source_ref,
                caption_kind=caption_kind,
                index=index,
            ).model_dump(mode="json")
            for index in evenly_sampled_indexes(len(document), MAX_RENDERED_SLIDES)
        ]
    finally:
        document.close()


def _render_page(
    *,
    document,
    fitz,
    output_root: Path,
    slide_root: str,
    course_id: str,
    lecture_id: str,
    source_ref: str,
    caption_kind: str,
    index: int,
) -> CanvasBlock:
    number = index + 1
    asset_path = f"{slide_root}/slide-{number:03}.png"
    output_path = output_root / asset_path
    if not output_path.exists():
        pixmap = document.load_page(index).get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        if pixmap.width * pixmap.height > MAX_RENDERED_PIXELS:
            raise PdfSlideAssetError("Rendered PDF page exceeds the pixel limit.")
        pixmap.save(output_path)
    label = "Compiled slide" if caption_kind == "compiled" else "Original slide"
    return CanvasBlock(
        id=f"{safe_id(lecture_id)}-original-slide-{number:03}",
        type="asset",
        asset_path=asset_path,
        asset_url=f"/course-assets/{course_id}/{lecture_id}/{asset_path}",
        caption=f"{label} {number} from {source_ref}",
    )


def _fitz():
    try:
        import fitz
    except ImportError as exc:
        raise PdfSlideAssetError("PyMuPDF is required to render original slides.") from exc
    return fitz


def _pdf_fingerprint(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
