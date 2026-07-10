from __future__ import annotations

from lecturepilot.bounded_processing import run_bounded


def read_pdf_text(path: str, *, max_pages: int, max_chars: int) -> str:
    return run_bounded(_read_pdf_text, path, max_pages, max_chars)


def pdf_page_count(path: str) -> int:
    return run_bounded(_pdf_page_count, path)


def _read_pdf_text(path: str, max_pages: int, max_chars: int) -> str:
    import fitz

    document = fitz.open(path)
    try:
        text = "\n\n".join(
            document.load_page(index).get_text("text")
            for index in range(min(len(document), max_pages))
        )
        return text[:max_chars]
    finally:
        document.close()


def _pdf_page_count(path: str) -> int:
    import fitz

    document = fitz.open(path)
    try:
        return len(document)
    finally:
        document.close()
