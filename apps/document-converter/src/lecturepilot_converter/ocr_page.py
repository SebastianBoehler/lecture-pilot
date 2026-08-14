from __future__ import annotations

import os
from typing import Literal

from pydantic import BaseModel, Field

from lecturepilot_converter.ocr_client import PaddleOcrClient, PaddleOcrError
from lecturepilot_converter.ocr_triage import decide_ocr


class OcrLocator(BaseModel):
    page: int = Field(ge=1)
    bbox: tuple[float, float, float, float]


class OcrPageResult(BaseModel):
    required: bool
    extraction: Literal["native", "ocr"]
    text: str
    warning: str | None = None
    locator: OcrLocator


def process_ocr_page(
    *,
    image: bytes,
    native_text: str,
    raster_ratio: float,
    page: int,
    width: float,
    height: float,
    client: PaddleOcrClient | None = None,
) -> OcrPageResult:
    decision = decide_ocr(
        len(native_text.strip()),
        _replacement_ratio(native_text),
        raster_ratio,
    )
    locator = OcrLocator(page=page, bbox=(0, 0, width, height))
    if not decision.required:
        return OcrPageResult(
            required=False,
            extraction="native",
            text=native_text,
            locator=locator,
        )
    configured = os.getenv("LECTUREPILOT_OCR_URL", "").strip()
    if client is None and configured:
        client = PaddleOcrClient(configured)
    if client is None:
        return _unavailable(native_text, locator, page)
    try:
        text = client.extract_markdown(image)
    except PaddleOcrError:
        return _unavailable(native_text, locator, page)
    return OcrPageResult(
        required=True,
        extraction="ocr",
        text=text,
        locator=locator,
    )


def _replacement_ratio(text: str) -> float:
    return text.count("\ufffd") / max(1, len(text))


def _unavailable(native_text: str, locator: OcrLocator, page: int) -> OcrPageResult:
    return OcrPageResult(
        required=True,
        extraction="native",
        text=native_text,
        warning=f"OCR required but unavailable for page {page}; the page image was preserved.",
        locator=locator,
    )
