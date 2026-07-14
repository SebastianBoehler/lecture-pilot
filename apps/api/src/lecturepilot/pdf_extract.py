from __future__ import annotations

from lecturepilot.bounded_processing import run_bounded
from lecturepilot.bounded_sampling import evenly_sampled_indexes


def read_pdf_text(path: str, *, max_pages: int, max_chars: int) -> str:
    return run_bounded(_read_pdf_text, path, max_pages, max_chars)


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
            f"{label}{document.load_page(index).get_text('text')[:page_budget]}"
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
