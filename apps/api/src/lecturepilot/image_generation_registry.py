from __future__ import annotations

import os

from lecturepilot.image_generation import ImageGenerator
from lecturepilot.image_generation_gemini import GeminiImageGenerator
from lecturepilot.image_generation_huggingface import HuggingFaceImageGenerator
from lecturepilot.image_generation_openrouter import OpenRouterImageGenerator


def image_generator_from_env() -> ImageGenerator | None:
    provider = os.getenv("LECTUREPILOT_IMAGE_PROVIDER", "auto").strip().lower()
    if provider in {"", "auto"}:
        return _auto_generator()
    if provider == "none":
        return None
    if provider == "gemini":
        return _gemini_generator()
    if provider in {"huggingface", "hf"}:
        return _huggingface_generator()
    if provider == "openrouter":
        return _openrouter_generator()
    return None


def _auto_generator() -> ImageGenerator | None:
    return _gemini_generator() or _openrouter_generator() or _huggingface_generator()


def _gemini_generator() -> GeminiImageGenerator | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return GeminiImageGenerator(
        api_key=api_key,
        model=os.getenv("GEMINI_IMAGE_MODEL") or "gemini-3.1-flash-image",
        aspect_ratio=os.getenv("GEMINI_IMAGE_ASPECT_RATIO") or "16:9",
        image_size=os.getenv("GEMINI_IMAGE_SIZE") or "1K",
    )


def _huggingface_generator() -> HuggingFaceImageGenerator | None:
    api_key = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
    if not api_key:
        return None
    return HuggingFaceImageGenerator(
        api_key=api_key,
        model=os.getenv("HUGGINGFACE_IMAGE_MODEL") or "black-forest-labs/FLUX.1-dev",
        width=_env_int("HUGGINGFACE_IMAGE_WIDTH", 1280),
        height=_env_int("HUGGINGFACE_IMAGE_HEIGHT", 720),
    )


def _openrouter_generator() -> OpenRouterImageGenerator | None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None
    return OpenRouterImageGenerator(
        api_key=api_key,
        model=os.getenv("OPENROUTER_IMAGE_MODEL") or "google/gemini-3.1-flash-image-preview",
        aspect_ratio=os.getenv("OPENROUTER_IMAGE_ASPECT_RATIO") or "16:9",
        image_size=os.getenv("OPENROUTER_IMAGE_SIZE") or "1K",
    )


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default
