from pathlib import Path

import fitz

from lecturepilot.document_converter_client import DocumentConverterError, OcrPageResult
from lecturepilot.pdf_extract import read_pdf_page_range_result


def _ocr_result(request: dict, text: str) -> OcrPageResult:
    return OcrPageResult.model_validate(
        {
            "required": True,
            "extraction": "ocr",
            "text": text,
            "warning": None,
            "locator": {
                "page": request["page"],
                "bbox": [0, 0, request["width"], request["height"]],
            },
        }
    )


def _read(source: Path, cache: Path | None = None):
    # The public reader parses in the bounded worker process; OCR happens in this process.
    return read_pdf_page_range_result(
        str(source), start_page=0, end_page=1, max_chars=20_000, ocr_cache_dir=cache
    )


def test_scanned_page_is_recognized_outside_the_bounded_parser(monkeypatch, tmp_path) -> None:
    source = tmp_path / "scan.pdf"
    _write_scanned_pdf(source, "Bayes-Regel nur als Bild")
    monkeypatch.setenv("LECTUREPILOT_DOCUMENT_CONVERTER_URL", "http://converter:8080")

    def ocr_page(_self, **request):
        assert request["page"] == 1
        assert request["raster_ratio"] > 0.9
        return _ocr_result(request, "Bayes-Regel aus dem Scan")

    monkeypatch.setattr("lecturepilot.pdf_page_ocr.DocumentConverterClient.ocr_page", ocr_page)

    result = _read(source)

    assert "[OCR-derived text]\nBayes-Regel aus dem Scan" in result.text
    assert result.warnings == ()


def test_recognized_pages_are_cached_but_failures_retry(monkeypatch, tmp_path) -> None:
    source = tmp_path / "scan.pdf"
    _write_scanned_pdf(source, "Cached scan")
    monkeypatch.setenv("LECTUREPILOT_DOCUMENT_CONVERTER_URL", "http://converter:8080")
    calls = []

    def ocr_page(_self, **request):
        calls.append(request["page"])
        if len(calls) == 1:
            raise DocumentConverterError("converter restarting")
        return _ocr_result(request, "Recognized once")

    monkeypatch.setattr("lecturepilot.pdf_page_ocr.DocumentConverterClient.ocr_page", ocr_page)
    cache = tmp_path / "ocr-cache"

    failed = _read(source, cache)
    recognized = _read(source, cache)
    cached = _read(source, cache)

    assert failed.warnings and "[OCR-derived text]" not in failed.text
    assert "Recognized once" in recognized.text and recognized.warnings == ()
    assert cached == recognized
    assert calls == [1, 1]


def test_scanned_pdf_preserves_page_and_warns_when_ocr_is_unavailable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "scan.pdf"
    _write_scanned_pdf(source, "Text only in pixels")
    monkeypatch.delenv("LECTUREPILOT_DOCUMENT_CONVERTER_URL", raising=False)

    result = _read(source)

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


def test_native_text_stays_verbatim_and_ocr_only_adds_new_lines(monkeypatch, tmp_path) -> None:
    from lecturepilot.pdf_page_ocr import PdfPageRecord, page_text

    monkeypatch.setenv("LECTUREPILOT_DOCUMENT_CONVERTER_URL", "http://converter:8080")
    monkeypatch.setattr(
        "lecturepilot.pdf_page_ocr.DocumentConverterClient.ocr_page",
        lambda _self, **request: _ocr_result(request, "Choosing a colour map\nGrayscale for CT"),
    )
    record = PdfPageRecord(
        number=12,
        native_text="Choosing a colour map 12\n",
        links=(),
        raster_ratio=0.9,
        width=600,
        height=800,
        image=b"png",
    )

    text, warning = page_text(record, tmp_path / "cache")

    # Approved source anchors quote native text, so it must stay first and unchanged.
    assert text == "Choosing a colour map 12\n[OCR-derived text]\nGrayscale for CT"
    assert warning is None
