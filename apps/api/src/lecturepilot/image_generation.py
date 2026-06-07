from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from lecturepilot.canvas_models import CanvasSection


class ImageGenerationError(RuntimeError):
    """Raised when a configured image model fails to return image bytes."""


class ImageGenerator(Protocol):
    def generate_infographic(self, *, prompt: str, section: CanvasSection) -> "GeneratedImage":
        """Generate one teaching infographic for a student canvas section."""


@dataclass(frozen=True)
class GeneratedImage:
    content: bytes
    mime_type: str
    extension: str
    caption: str
    provider: str
    model: str


def infographic_prompt(*, prompt: str, section: CanvasSection) -> str:
    section_text = _section_excerpt(section)
    return (
        "Create a rigorous academic teaching infographic for a university machine "
        "learning tutoring canvas. Use a clean white or off-white background, dark "
        "text, muted academic colors, sparse readable labels, simple arrows, and "
        "one clear conceptual flow. Avoid decorative gradients, mascots, stickers, "
        "marketing style, watermarks, and dense tiny text. The image should stand "
        "on its own as a helpful learning visual.\n\n"
        f"Student request: {prompt.strip()}\n"
        f"Canvas section title: {section.title}\n"
        f"Canvas section content: {section_text}"
    )


def extension_for_mime(mime_type: str) -> str:
    normalized = mime_type.split(";", 1)[0].strip().lower()
    if normalized == "image/jpeg":
        return "jpg"
    if normalized == "image/webp":
        return "webp"
    if normalized == "image/svg+xml":
        return "svg"
    return "png"


def image_from_data_url(value: str) -> tuple[bytes, str, str]:
    if not value.startswith("data:image/") or ";base64," not in value:
        raise ImageGenerationError("Image response was not a base64 data URL.")
    header, encoded = value.split(",", 1)
    mime_type = header.removeprefix("data:").split(";", 1)[0]
    return base64.b64decode(encoded), mime_type, extension_for_mime(mime_type)


def post_json(
    *,
    url: str,
    payload: dict,
    headers: dict[str, str],
    timeout_seconds: int,
) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise ImageGenerationError(f"Image generation failed: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ImageGenerationError("Image generation request failed.") from exc


def post_image_bytes(
    *,
    url: str,
    payload: dict,
    headers: dict[str, str],
    timeout_seconds: int,
) -> tuple[bytes, str]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read(), response.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise ImageGenerationError(f"Image generation failed: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ImageGenerationError("Image generation request failed.") from exc


def _section_excerpt(section: CanvasSection) -> str:
    parts: list[str] = []
    for block in section.blocks[:6]:
        if block.items:
            parts.extend(block.items[:5])
        elif block.text:
            parts.append(block.text)
    return " ".join(" ".join(parts).split())[:1800]
