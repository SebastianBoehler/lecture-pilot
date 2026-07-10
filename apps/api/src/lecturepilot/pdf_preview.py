from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from lecturepilot.bounded_processing import BoundedProcessingError, run_bounded


MAX_PREVIEW_PIXELS = 20_000_000


class PdfPreviewError(RuntimeError):
    """Raised when a PDF asset preview cannot be rendered."""


def render_pdf_preview(source_path: Path, preview_root: Path) -> Path:
    if source_path.suffix.lower() != ".pdf":
        raise PdfPreviewError("Only PDF files can be preview-rendered.")
    preview_root.mkdir(parents=True, exist_ok=True)
    preview_path = preview_root / f"{_preview_key(source_path)}.png"
    if preview_path.exists():
        return preview_path

    try:
        run_bounded(_render_preview, str(source_path), str(preview_path))
    except BoundedProcessingError as exc:
        raise PdfPreviewError(str(exc)) from exc
    except Exception as exc:
        raise PdfPreviewError("Could not render PDF preview.") from exc
    return preview_path


def _render_preview(source_path: str, preview_path: str) -> None:
    try:
        import fitz
    except ImportError as exc:
        raise PdfPreviewError("PyMuPDF is required to render PDF previews.") from exc
    document = fitz.open(source_path)
    try:
        if len(document) < 1:
            raise PdfPreviewError("PDF has no pages.")
        page = document.load_page(0)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        if pixmap.width * pixmap.height > MAX_PREVIEW_PIXELS:
            raise PdfPreviewError("PDF preview exceeds the pixel limit.")
        pixmap.save(preview_path)
    finally:
        document.close()


def _preview_key(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}"
    return sha256(raw.encode("utf-8")).hexdigest()[:32]
