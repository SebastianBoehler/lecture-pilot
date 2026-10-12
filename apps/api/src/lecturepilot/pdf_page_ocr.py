"""Text recognition for image-only PDF pages, outside the bounded PDF parser.

The bounded parser only renders candidate pages. Recognition calls the converter from the
calling worker thread, bounded per page by the converter client's timeout, and caches each
result by the SHA-256 of the rendered page image, so a page is recognized once rather than
on every proposal and draft. Failures and degraded results are not cached and retry later.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path

from lecturepilot.document_converter_client import DocumentConverterClient, DocumentConverterError
from lecturepilot.durable_files import atomic_write_json

OCR_CACHE_VERSION = 1


@dataclass(frozen=True)
class PdfPageRecord:
    number: int
    native_text: str
    links: tuple[str, ...]
    raster_ratio: float
    width: float
    height: float
    image: bytes | None = None  # Rendered PNG, only for pages that need recognition.


def page_text(record: PdfPageRecord, cache_dir: Path | None) -> tuple[str, str | None]:
    text, warning = record.native_text, None
    if record.image is not None:
        text, warning = _recognized_text(record, cache_dir)
    if record.links:
        text = f"{text.rstrip()}\n[Embedded links]\n" + "\n".join(
            f"- {uri}" for uri in record.links
        )
    return text, warning


def ocr_unavailable_warning(page_number: int) -> str:
    return f"OCR required but unavailable for page {page_number}; the page image was preserved."


def _recognized_text(record: PdfPageRecord, cache_dir: Path | None) -> tuple[str, str | None]:
    cache_path = (
        cache_dir / f"v{OCR_CACHE_VERSION}-{sha256(record.image).hexdigest()}.json"
        if cache_dir is not None
        else None
    )
    cached = _read_cache(cache_path)
    if cached is None:
        configured = os.getenv("LECTUREPILOT_DOCUMENT_CONVERTER_URL", "").strip()
        if not configured:
            return record.native_text, ocr_unavailable_warning(record.number)
        try:
            result = DocumentConverterClient(configured).ocr_page(
                image=record.image,
                native_text=record.native_text,
                raster_ratio=record.raster_ratio,
                page=record.number,
                width=record.width,
                height=record.height,
            )
        except (DocumentConverterError, RuntimeError):
            return record.native_text, ocr_unavailable_warning(record.number)
        cached = {
            "text": result.text if result.extraction == "ocr" else None,
            "warning": result.warning,
        }
        # A warning means recognition was degraded or unavailable: retry it next time.
        if cache_path is not None and result.warning is None:
            atomic_write_json(cache_path, cached)
    return _with_recognized_lines(record.native_text, cached["text"] or ""), cached["warning"]


def _with_recognized_lines(native: str, recognized: str) -> str:
    """Native text stays verbatim (approved source anchors quote it); OCR only adds lines."""
    known = " ".join(native.split()).casefold()
    extra = [
        line
        for line in recognized.splitlines()
        if line.strip() and " ".join(line.split()).casefold() not in known
    ]
    if not extra:
        return native
    prefix = f"{native.rstrip()}\n" if native.strip() else ""
    return prefix + "[OCR-derived text]\n" + "\n".join(extra)


def _read_cache(path: Path | None) -> dict | None:
    if path is None or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("text"), (str, type(None))):
        return None
    return {"text": payload["text"], "warning": payload.get("warning")}
