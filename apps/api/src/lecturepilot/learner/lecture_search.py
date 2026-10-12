"""Bounded text search over published, learner-visible canvas content.

Only teaching blocks are searched. Assessment blocks (checkpoints, quizzes, predictions,
interactive components) are skipped entirely so expected evidence, answer options and hidden
task wording can never surface in a result snippet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel, Field

from lecturepilot.canvas.canvas_models import CanvasBlock, CanvasDocument

MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 100
MAX_QUERY_TERMS = 8
MAX_RESULTS = 20
MAX_RESULTS_PER_LECTURE = 5
SNIPPET_RADIUS = 70

_SEARCHABLE_BLOCKS = frozenset({"paragraph", "list", "callout", "table", "asset", "video"})
_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_MARKUP = re.compile(r"[*_`#>|]+")
_SPACE = re.compile(r"\s+")


class LectureSearchHit(BaseModel):
    lecture_id: str
    lecture_title: str
    section_id: str
    section_title: str
    snippet: str = Field(max_length=3 * SNIPPET_RADIUS + 2)


class LectureSearchResult(BaseModel):
    results: list[LectureSearchHit] = Field(default_factory=list, max_length=MAX_RESULTS)
    truncated: bool = False


@dataclass(frozen=True)
class SearchableLecture:
    id: str
    title: str
    document: CanvasDocument


def normalize_query(raw: str) -> list[str]:
    """Return lower-case search terms or raise ValueError for an unusable query."""
    query = _SPACE.sub(" ", raw).strip()
    if len(query) < MIN_QUERY_LENGTH or len(query) > MAX_QUERY_LENGTH:
        raise ValueError(
            f"Search text must be {MIN_QUERY_LENGTH} to {MAX_QUERY_LENGTH} characters long."
        )
    terms = list(dict.fromkeys(term.casefold() for term in query.split(" ")))
    return terms[:MAX_QUERY_TERMS]


def search_lectures(lectures: list[SearchableLecture], terms: list[str]) -> LectureSearchResult:
    hits: list[tuple[int, int, int, LectureSearchHit]] = []
    for lecture_order, lecture in enumerate(lectures):
        lecture_hits = 0
        for section_order, section in enumerate(lecture.document.sections):
            texts = [
                text
                for block in section.blocks
                if block.type in _SEARCHABLE_BLOCKS
                for text in _block_texts(block)
            ]
            title = _plain(section.title)
            haystack = " ".join([title, *texts]).casefold()
            if not all(term in haystack for term in terms):
                continue
            title_matches = sum(term in title.casefold() for term in terms)
            hits.append(
                (
                    -title_matches,
                    lecture_order,
                    section_order,
                    LectureSearchHit(
                        lecture_id=lecture.id,
                        lecture_title=lecture.title,
                        section_id=section.id,
                        section_title=title,
                        snippet=_snippet(texts, terms),
                    ),
                )
            )
            lecture_hits += 1
            if lecture_hits >= MAX_RESULTS_PER_LECTURE:
                break
    hits.sort(key=lambda item: item[:3])
    return LectureSearchResult(
        results=[item[3] for item in hits[:MAX_RESULTS]],
        truncated=len(hits) > MAX_RESULTS,
    )


def _block_texts(block: CanvasBlock) -> list[str]:
    if block.type in {"asset", "video"}:
        values = [block.caption or ""]
    else:
        values = [block.text or "", *block.items]
    return [plain for value in values if (plain := _plain(value))]


def _plain(value: str) -> str:
    return _SPACE.sub(" ", _MARKUP.sub(" ", _LINK.sub(r"\1", value))).strip()


def _snippet(texts: list[str], terms: list[str]) -> str:
    for text in texts:
        folded = text.casefold()
        positions = [folded.find(term) for term in terms if term in folded]
        if not positions:
            continue
        start = max(0, min(positions) - SNIPPET_RADIUS)
        end = min(len(text), min(positions) + SNIPPET_RADIUS * 2)
        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(text) else ""
        return f"{prefix}{text[start:end].strip()}{suffix}"
    return texts[0][: SNIPPET_RADIUS * 2] if texts else ""
