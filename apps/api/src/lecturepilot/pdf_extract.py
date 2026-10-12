from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from lecturepilot.bounded_processing import run_bounded
from lecturepilot.bounded_sampling import evenly_sampled_indexes
from lecturepilot.document_converter_client import MAX_OCR_IMAGE_BYTES
from lecturepilot.pdf_page_ocr import PdfPageRecord, page_text


@dataclass(frozen=True)
class PdfTextExtraction:
    text: str
    warnings: tuple[str, ...]


def read_pdf_text(
    path: str, *, max_pages: int, max_chars: int, ocr_cache_dir: Path | None = None
) -> str:
    records = run_bounded(_sampled_page_records, path, max_pages)
    return _assemble(records, max_chars, ocr_cache_dir).text


def read_pdf_page_range_result(
    path: str,
    *,
    start_page: int,
    end_page: int,
    max_chars: int,
    ocr_cache_dir: Path | None = None,
) -> PdfTextExtraction:
    # The bounded worker only parses and renders; recognition runs here, outside its budget.
    records = run_bounded(_page_range_records, path, start_page, end_page)
    return _assemble(records, max_chars, ocr_cache_dir)


def pdf_page_count(path: str) -> int:
    return run_bounded(_pdf_page_count, path)


def pdf_requires_ocr(path: str, *, max_pages: int = 20) -> bool:
    return run_bounded(_pdf_requires_ocr, path, max_pages)


def _assemble(
    records: list[PdfPageRecord], max_chars: int, ocr_cache_dir: Path | None
) -> PdfTextExtraction:
    labels = [f"[PDF page {record.number}]\n" for record in records]
    separators_size = max(0, len(records) - 1) * 2
    content_budget = max(0, max_chars - sum(map(len, labels)) - separators_size)
    page_budget = content_budget // len(records) if records else 0
    warnings, chunks = [], []
    for record, label in zip(records, labels, strict=True):
        text, warning = page_text(record, ocr_cache_dir)
        chunks.append(f"{label}{text[:page_budget]}")
        if warning:
            warnings.append(warning)
    return PdfTextExtraction("\n\n".join(chunks), tuple(dict.fromkeys(warnings)))


def _sampled_page_records(path: str, max_pages: int) -> list[PdfPageRecord]:
    import fitz

    document = fitz.open(path)
    try:
        indexes = evenly_sampled_indexes(len(document), max_pages)
        return [_page_record(document.load_page(index), index + 1) for index in indexes]
    finally:
        document.close()


def _page_range_records(path: str, start_page: int, end_page: int) -> list[PdfPageRecord]:
    import fitz

    document = fitz.open(path)
    try:
        start = max(0, start_page)
        end = min(len(document), max(start, end_page))
        return [_page_record(document.load_page(index), index + 1) for index in range(start, end)]
    finally:
        document.close()


def _page_record(page: object, page_number: int) -> PdfPageRecord:
    native_text = page.get_text("text")
    raster_ratio = _raster_ratio(page)
    image = None
    if _ocr_candidate(native_text, raster_ratio):
        rendered = page.get_pixmap(matrix=_render_matrix(page), alpha=False).tobytes("png")
        image = rendered if len(rendered) <= MAX_OCR_IMAGE_BYTES else None
    return PdfPageRecord(
        number=page_number,
        native_text=native_text,
        links=tuple(_safe_page_links(page)),
        raster_ratio=raster_ratio,
        width=float(page.rect.width),
        height=float(page.rect.height),
        image=image,
    )


def _pdf_page_count(path: str) -> int:
    import fitz

    document = fitz.open(path)
    try:
        return len(document)
    finally:
        document.close()


def _pdf_requires_ocr(path: str, max_pages: int) -> bool:
    import fitz

    document = fitz.open(path)
    try:
        return any(
            _ocr_candidate(page.get_text("text"), _raster_ratio(page))
            for index in evenly_sampled_indexes(len(document), max_pages)
            if (page := document.load_page(index))
        )
    finally:
        document.close()


def _ocr_candidate(text: str, raster_ratio: float) -> bool:
    stripped = text.strip()
    replacement_ratio = text.count("\ufffd") / max(1, len(text))
    return bool(
        raster_ratio > 0
        and (
            not stripped
            or (len(stripped) < 400 and raster_ratio >= 0.5)
            or replacement_ratio >= 0.1
        )
    )


def _raster_ratio(page: object) -> float:
    area = float(page.rect.width * page.rect.height)
    if area <= 0:
        return 0.0
    covered = 0.0
    for image in page.get_image_info():
        bbox = image.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        left, top, right, bottom = map(float, bbox)
        covered += max(0.0, right - left) * max(0.0, bottom - top)
    return min(1.0, covered / area)


def _render_matrix(page: object):
    import fitz

    scale = 2 if page.rect.width * page.rect.height * 4 <= 20_000_000 else 1
    return fitz.Matrix(scale, scale)


def _safe_page_links(page: object) -> list[str]:
    links: list[str] = []
    for item in page.get_links():
        uri = str(item.get("uri") or "").strip()
        if urlsplit(uri).scheme.lower() not in {"http", "https"} or uri in links:
            continue
        links.append(uri[:1000])
    return links
