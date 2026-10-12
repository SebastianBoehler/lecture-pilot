"""In-process CPU OCR (RapidOCR / PP-OCR small ONNX models baked into the image).

Only confident lines become evidence: unreadable fragments from figures, comics or tiny
print are dropped instead of being passed on as teaching source text.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

from lecturepilot_converter.ocr_client import PaddleOcrError, _validate_image

MIN_LINE_CONFIDENCE = 0.85
MIN_LINE_ALNUM = 2
MAX_OCR_TEXT_CHARS = 60_000
MAX_OCR_THREADS = 4
CGROUP_CPU_MAX = Path("/sys/fs/cgroup/cpu.max")

_engine = None
_lock = Lock()


class LocalOcrEngine:
    """Same contract as the remote PaddleOCR client: image bytes in, Markdown text out."""

    def extract_markdown(self, image: bytes) -> str:
        _validate_image(image)
        try:
            with _lock:  # One page at a time bounds RAM inside the converter limits.
                result = _load()(image)
        except PaddleOcrError:
            raise
        except Exception as exc:  # noqa: BLE001 - any engine failure means "OCR unavailable"
            raise PaddleOcrError("Local OCR engine failed.") from exc
        return confident_text(result.txts or (), result.scores or ())


def confident_text(lines, scores) -> str:
    kept = [
        line.strip()
        for line, score in zip(lines, scores, strict=False)
        if score >= MIN_LINE_CONFIDENCE and sum(c.isalnum() for c in line) >= MIN_LINE_ALNUM
    ]
    return "\n".join(kept)[:MAX_OCR_TEXT_CHARS]


def _load():
    global _engine
    if _engine is None:
        try:
            from rapidocr import RapidOCR
        except ImportError as exc:
            raise PaddleOcrError("Local OCR engine is not installed.") from exc
        threads = ocr_threads()
        _engine = RapidOCR(
            params={
                "Global.log_level": "error",
                "EngineConfig.onnxruntime.intra_op_num_threads": threads,
                "EngineConfig.onnxruntime.inter_op_num_threads": 1,
            }
        )
    return _engine


def ocr_threads(cpu_max: Path = CGROUP_CPU_MAX) -> int:
    """Threads for the container's CPU quota, not the host's cores.

    onnxruntime defaults to one thread per host core for each model; under a 2-CPU quota that
    throttles OCR about tenfold and can exhaust the container's process limit.
    """
    try:
        quota, period = cpu_max.read_text().split()[:2]
        cpus = int(quota) // int(period) if quota != "max" else os.cpu_count() or 1
    except (OSError, ValueError):
        cpus = os.cpu_count() or 1
    return max(1, min(MAX_OCR_THREADS, cpus))
