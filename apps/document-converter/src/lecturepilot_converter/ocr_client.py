from __future__ import annotations

from base64 import b64encode
from urllib.parse import urlsplit

import httpx


MAX_OCR_IMAGE_BYTES = 20 * 1024 * 1024
MAX_OCR_RESPONSE_BYTES = 5 * 1024 * 1024
MAX_OCR_TEXT_CHARS = 60_000


class PaddleOcrError(RuntimeError):
    pass


class PaddleOcrClient:
    def __init__(self, base_url: str, *, transport: httpx.BaseTransport | None = None) -> None:
        self.base_url = _validated_base_url(base_url)
        self.transport = transport

    def extract_markdown(self, image: bytes) -> str:
        _validate_image(image)
        try:
            with httpx.Client(transport=self.transport, timeout=90) as client:
                response = client.post(
                    f"{self.base_url}/layout-parsing",
                    json={
                        "file": b64encode(image).decode("ascii"),
                        "fileType": 1,
                        "returnMarkdownImages": False,
                        "visualize": False,
                        "restructurePages": False,
                    },
                )
        except httpx.HTTPError as exc:
            raise PaddleOcrError("PaddleOCR worker is unavailable.") from exc
        if response.status_code != 200 or len(response.content) > MAX_OCR_RESPONSE_BYTES:
            raise PaddleOcrError("PaddleOCR worker rejected the page.")
        try:
            payload = response.json()
            results = payload["result"]["layoutParsingResults"]
            if payload.get("errorCode") != 0 or len(results) != 1:
                raise ValueError
            result = results[0]
            if not isinstance(result.get("prunedResult"), dict):
                raise ValueError
            text = result["markdown"]["text"].strip()
            if not text or len(text) > MAX_OCR_TEXT_CHARS:
                raise ValueError
        except (KeyError, TypeError, ValueError) as exc:
            message = "PaddleOCR must return exactly one page with bounded Markdown text."
            raise PaddleOcrError(message) from exc
        return text


def _validated_base_url(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise PaddleOcrError("PaddleOCR worker URL is invalid.")
    return value.rstrip("/")


def _validate_image(image: bytes) -> None:
    is_png = image.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpeg = image.startswith(b"\xff\xd8\xff")
    if not image or len(image) > MAX_OCR_IMAGE_BYTES or not (is_png or is_jpeg):
        raise PaddleOcrError("OCR input must be a bounded PNG or JPEG image.")
