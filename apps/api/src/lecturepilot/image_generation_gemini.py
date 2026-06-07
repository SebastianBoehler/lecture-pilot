from __future__ import annotations

import base64
import time

from lecturepilot.canvas_models import CanvasSection
from lecturepilot.image_generation import (
    GeneratedImage,
    ImageGenerationError,
    extension_for_mime,
    infographic_prompt,
    post_json,
)


class GeminiImageGenerator:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-3.1-flash-image",
        aspect_ratio: str = "16:9",
        image_size: str = "1K",
        timeout_seconds: int = 180,
        max_attempts: int = 2,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.aspect_ratio = aspect_ratio
        self.image_size = image_size
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max(1, min(max_attempts, 4))

    def generate_infographic(self, *, prompt: str, section: CanvasSection) -> GeneratedImage:
        prompt_text = (
            f"{infographic_prompt(prompt=prompt, section=section)}\n\n"
            f"Render the final image in {self.aspect_ratio} at about {self.image_size} resolution."
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
        }
        inline = self._post_with_retries(payload)
        mime_type = inline.get("mimeType") or inline.get("mime_type") or "image/png"
        return GeneratedImage(
            content=base64.b64decode(inline["data"]),
            mime_type=mime_type,
            extension=extension_for_mime(mime_type),
            caption=f"Generated with {self.model} as a teaching infographic",
            provider="gemini",
            model=self.model,
        )

    def _post_with_retries(self, payload: dict) -> dict:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = post_json(
                    url=f"https://generativelanguage.googleapis.com/v1/models/{self.model}:generateContent",
                    headers={"x-goog-api-key": self.api_key},
                    payload=payload,
                    timeout_seconds=self.timeout_seconds,
                )
                return _read_inline_image(response)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.max_attempts:
                    time.sleep(min(1.5 * attempt, 4.0))
        raise ImageGenerationError("Gemini image generation returned no image.") from last_error


def _read_inline_image(payload: dict) -> dict:
    for candidate in payload.get("candidates", []):
        content = candidate.get("content") if isinstance(candidate, dict) else None
        parts = content.get("parts", []) if isinstance(content, dict) else []
        for part in parts:
            if not isinstance(part, dict):
                continue
            inline = part.get("inlineData") or part.get("inline_data")
            if isinstance(inline, dict) and inline.get("data"):
                return inline
    raise ImageGenerationError("Gemini response did not include inline image data.")
