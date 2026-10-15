"""Normalized course titles for matching Alma/ILIAS course names to LecturePilot courses."""

from __future__ import annotations

import re
import unicodedata

_MODULE_CODE_PREFIX = re.compile(
    r"^\s*[^\W\d_]{2,}\s*-?\s*\d{3,}[^\W\d_]?\s*[:\-–—]?\s*", re.UNICODE
)


def course_title_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = _MODULE_CODE_PREFIX.sub("", normalized)
    return "".join(character for character in normalized if character.isalnum())
