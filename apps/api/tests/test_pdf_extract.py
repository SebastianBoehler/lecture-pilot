from pathlib import Path

import fitz

from lecturepilot.pdf_extract import read_pdf_text


def test_pdf_text_includes_safe_embedded_links(tmp_path: Path) -> None:
    path = tmp_path / "linked-slides.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Further reading")
    page.insert_link(
        {
            "kind": fitz.LINK_URI,
            "from": fitz.Rect(72, 55, 180, 80),
            "uri": "https://example.edu/reading",
        }
    )
    page.insert_link(
        {
            "kind": fitz.LINK_URI,
            "from": fitz.Rect(72, 90, 180, 110),
            "uri": "javascript:alert('unsafe')",
        }
    )
    document.save(path)
    document.close()

    extracted = read_pdf_text(str(path), max_pages=1, max_chars=500)

    assert "Further reading" in extracted
    assert "[Embedded links]" in extracted
    assert "https://example.edu/reading" in extracted
    assert "javascript:" not in extracted
