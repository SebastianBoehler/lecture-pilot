from __future__ import annotations

from lecturepilot.canvas_models import CanvasSection
from lecturepilot.image_generation import (
    GeneratedImage,
    extension_for_mime,
    infographic_prompt,
    post_image_bytes,
)


class HuggingFaceImageGenerator:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "black-forest-labs/FLUX.1-dev",
        width: int = 1280,
        height: int = 720,
        timeout_seconds: int = 180,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.width = width
        self.height = height
        self.timeout_seconds = timeout_seconds

    def generate_infographic(self, *, prompt: str, section: CanvasSection) -> GeneratedImage:
        payload = {
            "inputs": infographic_prompt(prompt=prompt, section=section),
            "parameters": {
                "width": self.width,
                "height": self.height,
                "negative_prompt": (
                    "decorative gradients, mascots, stickers, watermarks, tiny unreadable text"
                ),
            },
        }
        content, mime_type = post_image_bytes(
            url=f"https://api-inference.huggingface.co/models/{self.model}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            payload=payload,
            timeout_seconds=self.timeout_seconds,
        )
        return GeneratedImage(
            content=content,
            mime_type=mime_type,
            extension=extension_for_mime(mime_type),
            caption=f"Generated with Hugging Face model {self.model}",
            provider="huggingface",
            model=self.model,
        )
