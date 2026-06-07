from __future__ import annotations

from lecturepilot.canvas_models import CanvasSection
from lecturepilot.image_generation import (
    GeneratedImage,
    ImageGenerationError,
    image_from_data_url,
    infographic_prompt,
    post_json,
)


class OpenRouterImageGenerator:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "google/gemini-3.1-flash-image-preview",
        aspect_ratio: str = "16:9",
        image_size: str = "1K",
        timeout_seconds: int = 180,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.aspect_ratio = aspect_ratio
        self.image_size = image_size
        self.timeout_seconds = timeout_seconds

    def generate_infographic(self, *, prompt: str, section: CanvasSection) -> GeneratedImage:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": infographic_prompt(prompt=prompt, section=section)}],
            "modalities": ["image", "text"],
            "image_config": {"aspect_ratio": self.aspect_ratio, "image_size": self.image_size},
            "stream": False,
        }
        response = post_json(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "http://localhost",
                "X-Title": "LecturePilot",
            },
            payload=payload,
            timeout_seconds=self.timeout_seconds,
        )
        content, mime_type, extension = image_from_data_url(_read_image_data_url(response))
        return GeneratedImage(
            content=content,
            mime_type=mime_type,
            extension=extension,
            caption=f"Generated with OpenRouter model {self.model}",
            provider="openrouter",
            model=self.model,
        )


def _read_image_data_url(payload: dict) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ImageGenerationError("OpenRouter image response contained no choices.")
    message = choices[0].get("message")
    images = message.get("images") if isinstance(message, dict) else None
    if not isinstance(images, list) or not images:
        raise ImageGenerationError("OpenRouter image response contained no images.")
    first = images[0]
    image_url = first.get("image_url") if isinstance(first, dict) else None
    url = image_url.get("url") if isinstance(image_url, dict) else None
    if not isinstance(url, str):
        raise ImageGenerationError("OpenRouter image response contained no image URL.")
    return url
