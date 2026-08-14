from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import urlsplit

from lecturepilot.bounded_processing import run_bounded
from lecturepilot.bounded_sampling import evenly_sampled_indexes
from lecturepilot.document_converter_client import DocumentConverterClient, DocumentConverterError


@dataclass(frozen=True)
class PdfTextExtraction:
    text: str
    warnings: tuple[str, ...]


def read_pdf_text(path: str, *, max_pages: int, max_chars: int) -> str:
    return run_bounded(_read_pdf_text, path, max_pages, max_chars)


def read_pdf_page_range(path: str, *, start_page: int, end_page: int, max_chars: int) -> str:
    return run_bounded(_read_pdf_page_range, path, start_page, end_page, max_chars)


def read_pdf_page_range_result(
    path: str,
    *,
    start_page: int,
    end_page: int,
    max_chars: int,
) -> PdfTextExtraction:
    return run_bounded(_read_pdf_page_range_result, path, start_page, end_page, max_chars)


def pdf_page_count(path: str) -> int:
    return run_bounded(_pdf_page_count, path)


def _read_pdf_text(path: str, max_pages: int, max_chars: int) -> str:
    import fitz

    document = fitz.open(path)
    try:
        indexes = evenly_sampled_indexes(len(document), max_pages)
        labels = [f"[PDF page {index + 1}]\n" for index in indexes]
        separators_size = max(0, len(indexes) - 1) * 2
        content_budget = max(0, max_chars - sum(map(len, labels)) - separators_size)
        page_budget = content_budget // len(indexes) if indexes else 0
        chunks = []
        for index, label in zip(indexes, labels, strict=True):
            text, _warning = _page_text_with_ocr(document.load_page(index), index + 1)
            chunks.append(f"{label}{text[:page_budget]}")
        return "\n\n".join(chunks)
    finally:
        document.close()


def _pdf_page_count(path: str) -> int:
    import fitz

    document = fitz.open(path)
    try:
        return len(document)
    finally:
        document.close()


def _read_pdf_page_range(path: str, start_page: int, end_page: int, max_chars: int) -> str:
    return _read_pdf_page_range_result(path, start_page, end_page, max_chars).text


def _read_pdf_page_range_result(
    path: str,
    start_page: int,
    end_page: int,
    max_chars: int,
) -> PdfTextExtraction:
    import fitz

    document = fitz.open(path)
    try:
        start = max(0, start_page)
        end = min(len(document), max(start, end_page))
        indexes = list(range(start, end))
        labels = [f"[PDF page {index + 1}]\n" for index in indexes]
        separators_size = max(0, len(indexes) - 1) * 2
        content_budget = max(0, max_chars - sum(map(len, labels)) - separators_size)
        page_budget = content_budget // len(indexes) if indexes else 0
        warnings = []
        chunks = []
        for index, label in zip(indexes, labels, strict=True):
            text, warning = _page_text_with_ocr(document.load_page(index), index + 1)
            chunks.append(f"{label}{text[:page_budget]}")
            if warning:
                warnings.append(warning)
        return PdfTextExtraction("\n\n".join(chunks), tuple(dict.fromkeys(warnings)))
    finally:
        document.close()


def _page_text(page: object, max_chars: int) -> str:
    text = page.get_text("text")
    links = _safe_page_links(page)
    if not links:
        return text[:max_chars]
    link_section = "\n[Embedded links]\n" + "\n".join(f"- {uri}" for uri in links)
    link_section = link_section[: min(max_chars, max(256, max_chars // 3))]
    return f"{text[: max(0, max_chars - len(link_section))].rstrip()}{link_section}"[:max_chars]


def _page_text_with_ocr(page: object, page_number: int) -> tuple[str, str | None]:
    native_text = page.get_text("text")
    raster_ratio = _raster_ratio(page)
    warning = None
    text = native_text
    if _ocr_candidate(native_text, raster_ratio):
        configured = os.getenv("LECTUREPILOT_DOCUMENT_CONVERTER_URL", "").strip()
        if not configured:
            warning = _ocr_unavailable_warning(page_number)
        else:
            try:
                pixmap = page.get_pixmap(matrix=_render_matrix(page), alpha=False)
                result = DocumentConverterClient(configured).ocr_page(
                    image=pixmap.tobytes("png"),
                    native_text=native_text,
                    raster_ratio=raster_ratio,
                    page=page_number,
                    width=float(page.rect.width),
                    height=float(page.rect.height),
                )
            except (DocumentConverterError, RuntimeError):
                warning = _ocr_unavailable_warning(page_number)
            else:
                warning = result.warning
                if result.extraction == "ocr":
                    text = f"[OCR-derived text]\n{result.text}"
    links = _safe_page_links(page)
    if links:
        text = f"{text.rstrip()}\n[Embedded links]\n" + "\n".join(f"- {uri}" for uri in links)
    return text, warning


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


def _ocr_unavailable_warning(page_number: int) -> str:
    return f"OCR required but unavailable for page {page_number}; the page image was preserved."


def _safe_page_links(page: object) -> list[str]:
    links: list[str] = []
    for item in page.get_links():
        uri = str(item.get("uri") or "").strip()
        if urlsplit(uri).scheme.lower() not in {"http", "https"} or uri in links:
            continue
        links.append(uri[:1000])
    return links
