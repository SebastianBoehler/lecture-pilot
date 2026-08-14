from __future__ import annotations

from urllib.parse import urlsplit

from lecturepilot.bounded_processing import run_bounded
from lecturepilot.bounded_sampling import evenly_sampled_indexes


def read_pdf_text(path: str, *, max_pages: int, max_chars: int) -> str:
    return run_bounded(_read_pdf_text, path, max_pages, max_chars)


def read_pdf_page_range(path: str, *, start_page: int, end_page: int, max_chars: int) -> str:
    return run_bounded(_read_pdf_page_range, path, start_page, end_page, max_chars)


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
        chunks = [
            f"{label}{_page_text(document.load_page(index), page_budget)}"
            for index, label in zip(indexes, labels, strict=True)
        ]
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
        return "\n\n".join(
            f"{label}{_page_text(document.load_page(index), page_budget)}"
            for index, label in zip(indexes, labels, strict=True)
        )
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


def _safe_page_links(page: object) -> list[str]:
    links: list[str] = []
    for item in page.get_links():
        uri = str(item.get("uri") or "").strip()
        if urlsplit(uri).scheme.lower() not in {"http", "https"} or uri in links:
            continue
        links.append(uri[:1000])
    return links
