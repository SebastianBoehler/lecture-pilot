from __future__ import annotations

import os
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from lecturepilot.models import YoutubeDuration, YoutubeSearchResponse, YoutubeVideoCandidate


class YoutubeDiscoveryError(RuntimeError):
    """Raised when YouTube candidate discovery cannot complete."""


FetchJson = Callable[[str, dict[str, str | int]], dict[str, Any]]

_WORD_RE = re.compile(r"[a-z0-9]+")
_SHORT_MARKERS_RE = re.compile(r"(?:#shorts\b|#short\b|youtube\s+shorts?)", re.IGNORECASE)
_STOPWORDS = {
    "and",
    "are",
    "for",
    "from",
    "how",
    "into",
    "the",
    "this",
    "what",
    "with",
    "your",
}


class YoutubeDiscovery:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        preferred_language: str = "en",
        min_duration_seconds: int = 90,
        fetch_json: FetchJson | None = None,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.preferred_language = preferred_language.strip().lower() or "en"
        self.min_duration_seconds = max(0, int(min_duration_seconds))
        self.fetch_json = fetch_json or self._fetch_json

    @classmethod
    def from_env(cls) -> "YoutubeDiscovery":
        return cls(
            api_key=os.environ.get("YOUTUBE_API_KEY"),
            preferred_language=os.environ.get("YOUTUBE_PREFERRED_LANGUAGE", "en"),
            min_duration_seconds=_env_int("YOUTUBE_MIN_DURATION_SECONDS", 90),
        )

    def search(self, query: str, *, max_results: int = 5) -> YoutubeSearchResponse:
        normalized_query = query.strip()
        if not normalized_query:
            raise YoutubeDiscoveryError("YouTube search query cannot be empty.")
        limited_results = max(1, min(max_results, 10))
        fetched_results = max(limited_results, min(limited_results * 3, 15))
        search_payload = self.fetch_json(
            "search",
            {
                "part": "snippet",
                "type": "video",
                "q": normalized_query,
                "maxResults": fetched_results,
                "order": "relevance",
                "relevanceLanguage": self.preferred_language,
                "safeSearch": "moderate",
                "videoEmbeddable": "true",
            },
        )
        video_ids = _video_ids(search_payload)
        candidates = self._candidate_details(video_ids, query=normalized_query)
        return YoutubeSearchResponse(
            query=normalized_query,
            items=candidates[:limited_results],
            next_page_token=search_payload.get("nextPageToken"),
        )

    def _candidate_details(
        self, video_ids: list[str], *, query: str
    ) -> list[YoutubeVideoCandidate]:
        if not video_ids:
            return []
        details_payload = self.fetch_json(
            "videos",
            {
                "part": "snippet,contentDetails,statistics",
                "id": ",".join(video_ids),
                "maxResults": len(video_ids),
            },
        )
        by_id = {_item_id(item): item for item in _payload_items(details_payload)}
        candidates = [
            _candidate_from_item(by_id[video_id], query=query)
            for video_id in video_ids
            if video_id in by_id
        ]
        candidates = [candidate for candidate in candidates if self._keeps_candidate(candidate)]
        return sorted(candidates, key=_rank_key, reverse=True)

    def _keeps_candidate(self, candidate: YoutubeVideoCandidate) -> bool:
        if (
            candidate.duration.seconds is not None
            and candidate.duration.seconds < self.min_duration_seconds
        ):
            return False
        return not _SHORT_MARKERS_RE.search(" ".join([candidate.title, candidate.description]))

    def _fetch_json(self, path: str, params: dict[str, str | int]) -> dict[str, Any]:
        if not self.api_key:
            raise YoutubeDiscoveryError("YOUTUBE_API_KEY is not configured.")
        query = urlencode({**params, "key": self.api_key})
        request = Request(
            f"https://www.googleapis.com/youtube/v3/{path}?{query}",
            headers={"Accept": "application/json"},
        )
        try:
            import json

            with urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - surface provider detail to admin UI.
            raise YoutubeDiscoveryError(f"YouTube API request failed: {exc}") from exc


def _candidate_from_item(item: dict[str, Any], *, query: str) -> YoutubeVideoCandidate:
    snippet = item.get("snippet") or {}
    duration = _duration((item.get("contentDetails") or {}).get("duration"))
    statistics = item.get("statistics") or {}
    view_count = _optional_int(statistics.get("viewCount"))
    candidate = YoutubeVideoCandidate(
        video_id=_item_id(item),
        title=_limited_text(snippet.get("title"), 200) or "Untitled YouTube video",
        channel_title=_limited_text(snippet.get("channelTitle"), 200) or "Unknown channel",
        description=_limited_text(snippet.get("description"), 4000),
        url=f"https://www.youtube.com/watch?v={_item_id(item)}",
        thumbnail_url=_thumbnail_url(snippet.get("thumbnails") or {}),
        published_at=str(snippet.get("publishedAt") or "") or None,
        view_count=view_count,
        duration=duration,
    )
    score, reason = _score_candidate(candidate, query=query)
    return candidate.model_copy(update={"score": score, "reason": reason})


def _score_candidate(candidate: YoutubeVideoCandidate, *, query: str) -> tuple[float, str]:
    query_terms = _terms(query)
    video_terms = _terms(
        " ".join([candidate.title, candidate.channel_title, candidate.description])
    )
    overlap = len(query_terms & video_terms)
    duration_bonus = 1.0 if 180 <= (candidate.duration.seconds or 0) <= 1800 else 0.3
    view_bonus = min((candidate.view_count or 0) / 100_000, 3.0)
    score = (overlap * 3.0) + duration_bonus + view_bonus
    return round(
        score, 2
    ), f"{overlap} query terms matched; duration and views used as tie breakers."


def _rank_key(candidate: YoutubeVideoCandidate) -> tuple[float, int, int]:
    return (candidate.score, candidate.view_count or 0, candidate.duration.seconds or 0)


def _payload_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _video_ids(payload: dict[str, Any]) -> list[str]:
    return [
        str((item.get("id") or {}).get("videoId") or "").strip()
        for item in _payload_items(payload)
        if str((item.get("id") or {}).get("videoId") or "").strip()
    ]


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or "").strip()


def _duration(value: str | None) -> YoutubeDuration:
    seconds = _parse_iso_duration(value)
    return YoutubeDuration(iso8601=value, seconds=seconds, display=_format_seconds(seconds))


def _parse_iso_duration(value: str | None) -> int | None:
    match = re.fullmatch(
        r"P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?",
        str(value or ""),
        re.IGNORECASE,
    )
    if not match:
        return None
    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return (((days * 24) + hours) * 60 + minutes) * 60 + seconds


def _format_seconds(seconds: int | None) -> str | None:
    if seconds is None:
        return None
    minutes, rest = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{rest:02d}" if hours else f"{minutes}:{rest:02d}"


def _thumbnail_url(thumbnails: dict[str, Any]) -> str | None:
    for key in ("maxres", "standard", "high", "medium", "default"):
        url = (thumbnails.get(key) or {}).get("url")
        if isinstance(url, str) and 0 < len(url) <= 500:
            return url.strip()
    return None


def _limited_text(value: object, max_length: int) -> str:
    return str(value or "").strip()[:max_length]


def _optional_int(value: object) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _terms(value: str) -> set[str]:
    return {
        _stem(raw)
        for raw in _WORD_RE.findall(value.lower())
        if raw not in _STOPWORDS and len(raw) >= 3
    }


def _stem(value: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(value) > len(suffix) + 3 and value.endswith(suffix):
            return value[: -len(suffix)]
    return value


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default
