from __future__ import annotations

from dataclasses import dataclass


MIN_NATIVE_CHARS = 400
HIGH_REPLACEMENT_RATIO = 0.1
HIGH_RASTER_RATIO = 0.5


@dataclass(frozen=True)
class OcrDecision:
    required: bool
    reasons: tuple[str, ...]


def decide_ocr(chars: int, replacement_ratio: float, raster_ratio: float) -> OcrDecision:
    if chars < 0 or not 0 <= replacement_ratio <= 1 or not 0 <= raster_ratio <= 1:
        raise ValueError("OCR statistics are outside their accepted bounds.")
    reasons = []
    if chars == 0 and raster_ratio > 0:
        reasons.append("no native text")
    elif chars < MIN_NATIVE_CHARS and raster_ratio >= HIGH_RASTER_RATIO:
        reasons.append("insufficient native text")
    if replacement_ratio >= HIGH_REPLACEMENT_RATIO and raster_ratio > 0:
        reasons.append("corrupt native text")
    if raster_ratio >= HIGH_RASTER_RATIO and reasons:
        reasons.append("raster-dominant page")
    return OcrDecision(required=bool(reasons), reasons=tuple(reasons))
