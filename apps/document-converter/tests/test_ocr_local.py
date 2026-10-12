import importlib.util

import pytest

from lecturepilot_converter import ocr_local
from lecturepilot_converter.ocr_client import PaddleOcrClient, PaddleOcrError
from lecturepilot_converter.ocr_local import LocalOcrEngine, confident_text
from lecturepilot_converter.ocr_page import configured_ocr_client, process_ocr_page

PNG = b"\x89PNG\r\n\x1a\nscan"


def page(client=None, native_text=""):
    return process_ocr_page(
        image=PNG,
        native_text=native_text,
        raster_ratio=1.0,
        page=3,
        width=800,
        height=600,
        client=client,
    )


def test_only_confident_readable_lines_become_evidence():
    lines = ["Übertragungsfunktion", "JHMW HI", "o", "w^T x", "Gefäße im Schädel"]
    scores = [0.99, 0.70, 0.95, 0.91, 0.97]
    assert confident_text(lines, scores) == "Übertragungsfunktion\nw^T x\nGefäße im Schädel"


def test_engine_selection_prefers_remote_worker_then_local_cpu(monkeypatch):
    monkeypatch.delenv("LECTUREPILOT_OCR_URL", raising=False)
    monkeypatch.delenv("LECTUREPILOT_OCR_ENGINE", raising=False)
    assert configured_ocr_client() is None
    monkeypatch.setenv("LECTUREPILOT_OCR_ENGINE", "RapidOCR")
    assert isinstance(configured_ocr_client(), LocalOcrEngine)
    monkeypatch.setenv("LECTUREPILOT_OCR_URL", "http://ocr-worker:8080")
    assert isinstance(configured_ocr_client(), PaddleOcrClient)


class _Result:
    def __init__(self, txts, scores):
        self.txts, self.scores = txts, scores


def test_local_text_is_marked_as_ocr(monkeypatch):
    monkeypatch.setattr(ocr_local, "_engine", lambda image: _Result(["Volume rendering"], [0.98]))
    result = page(LocalOcrEngine())
    assert (result.extraction, result.text, result.warning) == ("ocr", "Volume rendering", None)


def test_page_without_confident_text_keeps_native_text_without_warning(monkeypatch):
    monkeypatch.setattr(ocr_local, "_engine", lambda image: _Result(["~~"], [0.4]))
    result = page(LocalOcrEngine(), native_text="Figure")
    assert (result.extraction, result.text, result.warning) == ("native", "Figure", None)


@pytest.mark.parametrize("failure", [RuntimeError("onnx crashed"), PaddleOcrError("missing")])
def test_engine_failure_preserves_page_with_warning(monkeypatch, failure):
    def broken(image):
        raise failure

    monkeypatch.setattr(ocr_local, "_engine", broken)
    result = page(LocalOcrEngine())
    assert result.extraction == "native"
    assert result.warning.startswith("OCR required but unavailable for page 3")


def test_invalid_image_is_rejected_before_the_engine_runs():
    with pytest.raises(PaddleOcrError):
        LocalOcrEngine().extract_markdown(b"not an image")


@pytest.mark.skipif(importlib.util.find_spec("rapidocr") is None, reason="OCR engine not installed")
def test_real_engine_reads_a_rendered_line():
    from io import BytesIO

    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (900, 160), "white")
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 48)
    except OSError:
        font = ImageFont.load_default(size=48)
    ImageDraw.Draw(image).text((30, 50), "Volume rendering pipeline", fill="black", font=font)
    output = BytesIO()
    image.save(output, format="PNG")
    text = LocalOcrEngine().extract_markdown(output.getvalue())
    assert "rendering" in text.casefold()


@pytest.mark.parametrize(
    ("cpu_max", "expected"),
    [("200000 100000\n", 2), ("50000 100000\n", 1), ("max 100000\n", 4), (None, 4)],
)
def test_ocr_threads_follow_the_container_cpu_quota(tmp_path, monkeypatch, cpu_max, expected):
    path = tmp_path / "cpu.max"
    if cpu_max is not None:
        path.write_text(cpu_max)
    monkeypatch.setattr(ocr_local.os, "cpu_count", lambda: 14)
    assert ocr_local.ocr_threads(path) == expected
