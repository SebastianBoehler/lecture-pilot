import io
import json
from urllib.error import HTTPError

import pytest

from lecturepilot.youtube_discovery import YoutubeDiscovery, YoutubeDiscoveryError


def test_youtube_discovery_normalizes_and_ranks_video_candidates() -> None:
    discovery = YoutubeDiscovery(api_key="test", fetch_json=_fake_fetch_json)

    response = discovery.search("bayesian decision theory", max_results=2)

    assert response.query == "bayesian decision theory"
    assert [item.video_id for item in response.items] == ["bbbbbbbbbbb", "aaaaaaaaaaa"]
    assert response.items[0].duration.display == "12:30"
    assert response.items[0].thumbnail_url == "https://img.example/high.jpg"
    assert response.items[0].score > response.items[1].score


def test_youtube_discovery_filters_shorts_and_too_short_videos() -> None:
    discovery = YoutubeDiscovery(
        api_key="test", min_duration_seconds=120, fetch_json=_fake_fetch_json
    )

    response = discovery.search("bayesian decision theory", max_results=5)

    assert "ccccccccccc" not in [item.video_id for item in response.items]
    assert "ddddddddddd" not in [item.video_id for item in response.items]


def test_youtube_discovery_bounds_untrusted_provider_metadata() -> None:
    def fetch_json(path: str, _params: dict[str, str | int]) -> dict:
        if path == "search":
            return {"items": [{"id": {"videoId": "eeeeeeeeeee"}}]}
        item = _video("eeeeeeeeeee", "T" * 300, "PT10M", 1)
        item["snippet"]["channelTitle"] = "C" * 300
        item["snippet"]["description"] = "D" * 5000
        return {"items": [item]}

    response = YoutubeDiscovery(api_key="test", fetch_json=fetch_json).search("bounded metadata")

    assert len(response.items[0].title) == 200
    assert len(response.items[0].channel_title) == 200
    assert len(response.items[0].description) == 4000


def _fake_fetch_json(path: str, _params: dict[str, str | int]) -> dict:
    if path == "search":
        return {
            "items": [
                {"id": {"videoId": "aaaaaaaaaaa"}},
                {"id": {"videoId": "bbbbbbbbbbb"}},
                {"id": {"videoId": "ccccccccccc"}},
                {"id": {"videoId": "ddddddddddd"}},
            ]
        }
    return {
        "items": [
            _video("aaaaaaaaaaa", "Bayes rule introduction", "PT8M", 8000),
            _video("bbbbbbbbbbb", "Bayesian decision theory and risk", "PT12M30S", 40_000),
            _video("ccccccccccc", "Bayes theorem #shorts", "PT3M", 50_000),
            _video("ddddddddddd", "Bayes in 30 seconds", "PT30S", 200_000),
        ]
    }


def _video(video_id: str, title: str, duration: str, views: int) -> dict:
    return {
        "id": video_id,
        "snippet": {
            "title": title,
            "channelTitle": "ML Course",
            "description": "Bayesian classifiers, posterior probabilities, and decision risk.",
            "publishedAt": "2026-01-01T00:00:00Z",
            "thumbnails": {"high": {"url": "https://img.example/high.jpg"}},
        },
        "contentDetails": {"duration": duration},
        "statistics": {"viewCount": str(views)},
    }


def _http_error(status: int, reason: str):
    body = json.dumps({"error": {"errors": [{"reason": reason}], "message": "raw detail"}})
    return HTTPError("https://www.googleapis.com", status, "Bad", {}, io.BytesIO(body.encode()))


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (_http_error(400, "badRequest"), "YouTube rejected the configured API key"),
        (_http_error(403, "quotaExceeded"), "daily YouTube search quota is used up"),
        (OSError("connection reset"), "YouTube search is unavailable right now"),
    ],
)
def test_youtube_failures_explain_the_next_step_without_raw_http_detail(
    monkeypatch, error, message
) -> None:
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr("lecturepilot.youtube_discovery.urlopen", fail)
    with pytest.raises(YoutubeDiscoveryError) as raised:
        YoutubeDiscovery(api_key="test").search("clustering", max_results=1)
    assert message in str(raised.value)
    assert "continue without videos" in str(raised.value)
    assert "HTTP Error" not in str(raised.value)
