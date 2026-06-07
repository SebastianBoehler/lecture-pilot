from __future__ import annotations

from hashlib import sha256
from pathlib import Path


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
        import fitz
    except ImportError as exc:
        raise PdfPreviewError("PyMuPDF is required to render PDF previews.") from exc

    try:
        document = fitz.open(source_path)
        page = document.load_page(0)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        pixmap.save(preview_path)
        document.close()
    except Exception as exc:
        raise PdfPreviewError(f"Could not render PDF preview: {source_path}") from exc
    return preview_path


def _preview_key(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}"
    return sha256(raw.encode("utf-8")).hexdigest()[:32]
