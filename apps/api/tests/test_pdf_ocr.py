from pathlib import Path

import fitz

from lecturepilot.document_converter_client import OcrPageResult
from lecturepilot.pdf_extract import _read_pdf_page_range_result


def test_scanned_pdf_page_uses_source_located_ocr(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "scan.pdf"
    _write_scanned_pdf(source, "Bayes-Regel nur als Bild")
    monkeypatch.setenv("LECTUREPILOT_DOCUMENT_CONVERTER_URL", "http://converter:8080")

    def ocr_page(_self, **request):
        assert request["page"] == 1
        assert request["raster_ratio"] > 0.9
        return OcrPageResult.model_validate(
            {
                "required": True,
                "extraction": "ocr",
                "text": "Bayes-Regel aus dem Scan",
                "warning": None,
                "locator": {"page": 1, "bbox": [0, 0, request["width"], request["height"]]},
            }
        )

    monkeypatch.setattr(
        "lecturepilot.pdf_extract.DocumentConverterClient.ocr_page",
        ocr_page,
    )

    result = _read_pdf_page_range_result(str(source), 0, 1, 20_000)

    assert "[OCR-derived text]" in result.text
    assert "Bayes-Regel aus dem Scan" in result.text
    assert result.warnings == ()


def test_scanned_pdf_preserves_page_and_warns_when_ocr_is_unavailable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "scan.pdf"
    _write_scanned_pdf(source, "Text only in pixels")
    monkeypatch.delenv("LECTUREPILOT_DOCUMENT_CONVERTER_URL", raising=False)

    result = _read_pdf_page_range_result(str(source), 0, 1, 20_000)

    assert "[OCR-derived text]" not in result.text
    assert result.warnings == (
        "OCR required but unavailable for page 1; the page image was preserved.",
    )


def _write_scanned_pdf(path: Path, text: str) -> None:
    native = fitz.open()
    page = native.new_page(width=600, height=800)
    page.insert_text((72, 100), text, fontsize=24)
    png = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png")
    native.close()

    scanned = fitz.open()
    scanned_page = scanned.new_page(width=600, height=800)
    scanned_page.insert_image(scanned_page.rect, stream=png)
    scanned.save(path)
    scanned.close()
