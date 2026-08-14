from __future__ import annotations

import re


_DIRECT_IMAGE_REQUEST = re.compile(
    r"\b(?:create|generate|add|make|draw|render|insert|produce|return)\s+"
    r"(?:me\s+)?(?:an?\s+|the\s+)?(?:real\s+|pixel-based\s+|raster\s+|infographic\s+)*"
    r"(?:image|picture|photo(?:graph)?|png(?:\s+image)?|jpe?g(?:\s+image)?|bitmap|raster|pixel\s+art)\b"
    r"(?:\s+asset)?"
    r"(?=\s+(?:of|for|to|showing|depicting|illustrating|explaining|comparing)\b|[\s.!?,]*$)",
    re.IGNORECASE,
)
_PRESENT_IMAGE_REQUEST = re.compile(
    r"\b(?:give|show)\s+(?:me\s+)?(?:an?\s+|the\s+)"
    r"(?:real\s+|pixel-based\s+|raster\s+)*"
    r"(?:image|picture|photo(?:graph)?|png(?:\s+image)?|jpe?g(?:\s+image)?|bitmap)\b",
    re.IGNORECASE,
)
_FORMAT_REQUEST = re.compile(
    r"\b(?:export|save|return|render|turn|convert)\b[^\n.!?]{0,60}"
    r"\b(?:as|to|into)\s+(?:an?\s+|the\s+)?"
    r"(?:png|jpe?g|bitmap|raster(?:\s+image)?)(?:\s+(?:image|file))?\b",
    re.IGNORECASE,
)
_GERMAN_IMAGE_REQUEST = re.compile(
    r"\b(?:erstelle|erzeuge|zeichne|rendere|f(?:ü|ue)ge)\s+(?:mir\s+)?"
    r"(?:ein(?:e|en)?\s+)?(?:rasterbild|bild|foto|png(?:-bild)?|jpe?g(?:-bild)?)\b",
    re.IGNORECASE,
)
_GERMAN_FORMAT_REQUEST = re.compile(
    r"\b(?:exportiere|speichere|rendere|wandle)\b[^\n.!?]{0,60}"
    r"\b(?:als|in)\s+(?:ein(?:e|en)?\s+)?(?:png|jpe?g|rasterbild)\b",
    re.IGNORECASE,
)


def is_explicit_raster_request(message: str) -> bool:
    return any(
        pattern.search(message)
        for pattern in (
            _DIRECT_IMAGE_REQUEST,
            _PRESENT_IMAGE_REQUEST,
            _FORMAT_REQUEST,
            _GERMAN_IMAGE_REQUEST,
            _GERMAN_FORMAT_REQUEST,
        )
    )
