from __future__ import annotations

import re
from threading import Lock
from typing import Any
import unicodedata

from pydantic import BaseModel, Field


class UniversityCourseSearchError(RuntimeError):
    """Raised when the public Alma course search cannot be queried safely."""


class UniversityCourseSuggestion(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    number: str | None = Field(default=None, max_length=80)
    instructor: str | None = Field(default=None, max_length=200)


class UniversityCourseSuggestionResult(BaseModel):
    items: list[UniversityCourseSuggestion]


class AlmaUniversityCourseSearch:
    def __init__(self) -> None:
        self._term_values: dict[str, str] = {}
        self._term_lock = Lock()

    def search(
        self,
        *,
        query: str,
        term: str,
        limit: int,
    ) -> list[UniversityCourseSuggestion]:
        try:
            # Keep the import lazy: university login support is optional, while this Alma page is public.
            from tue_api_wrapper import AlmaClient
            from tue_api_wrapper.alma_course_search_client import search_courses
        except ImportError as exc:
            raise UniversityCourseSearchError("tue-api-wrapper is unavailable.") from exc

        client = AlmaClient(timeout_seconds=15)
        try:
            term_value = self._resolve_term_value(client, search_courses, term)
            page = search_courses(
                client,
                query=query,
                term=term_value,
                limit=limit,
            )
            return _suggestions(page.results)
        except UniversityCourseSearchError:
            raise
        except Exception as exc:
            raise UniversityCourseSearchError("Alma course search failed.") from exc
        finally:
            client.session.close()

    def _resolve_term_value(self, client: Any, search_courses: Any, term: str) -> str:
        key = alma_term_key(term)
        with self._term_lock:
            cached = self._term_values.get(key)
        if cached:
            return cached

        page = search_courses(client)
        resolved = {alma_term_key(option.label): option.value for option in page.term_options}
        with self._term_lock:
            self._term_values.update(resolved)
        if key not in resolved:
            raise UniversityCourseSearchError("The requested Alma term is unavailable.")
        return resolved[key]


def alma_term_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    season = "sommer" if "sommer" in normalized else "winter" if "winter" in normalized else ""
    year_match = re.search(r"\b(20\d{2})\b", normalized)
    if season and year_match:
        return f"{season}:{year_match.group(1)}"
    return "".join(character for character in normalized if character.isalnum())


def _suggestions(results: Any) -> list[UniversityCourseSuggestion]:
    suggestions: list[UniversityCourseSuggestion] = []
    seen: set[str] = set()
    for item in results:
        title = str(item.title).strip()
        key = title.casefold()
        if not title or key in seen:
            continue
        seen.add(key)
        suggestions.append(
            UniversityCourseSuggestion(
                title=title,
                number=item.number,
                instructor=item.responsible_lecturer or item.lecturer,
            )
        )
    return suggestions
