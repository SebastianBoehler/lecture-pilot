import json

import httpx
import pytest

from lecturepilot_converter.ocr_client import PaddleOcrClient, PaddleOcrError
from lecturepilot_converter.ocr_triage import decide_ocr


@pytest.mark.parametrize(
    ("chars", "replacement_ratio", "raster_ratio", "required"),
    [
        (0, 0.0, 1.0, True),
        (800, 0.0, 0.1, False),
        (120, 0.2, 0.8, True),
        (0, 0.0, 0.0, False),
    ],
)
def test_ocr_decision(
    chars: int,
    replacement_ratio: float,
    raster_ratio: float,
    required: bool,
) -> None:
    assert decide_ocr(chars, replacement_ratio, raster_ratio).required is required


def test_paddle_client_requests_one_image_without_binary_outputs() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url.path == "/layout-parsing"
        assert payload["fileType"] == 1
        assert payload["returnMarkdownImages"] is False
        assert payload["visualize"] is False
        return httpx.Response(
            200,
            json={
                "errorCode": 0,
                "result": {
                    "layoutParsingResults": [
                        {
                            "prunedResult": {},
                            "markdown": {"text": "# Vorlesung\n\nBayes-Regel"},
                        }
                    ]
                },
            },
        )

    client = PaddleOcrClient(
        "http://ocr:8080",
        transport=httpx.MockTransport(respond),
    )

    assert client.extract_markdown(b"\x89PNG\r\n\x1a\nscan") == "# Vorlesung\n\nBayes-Regel"


def test_paddle_client_rejects_multi_page_response_for_one_image() -> None:
    response = {
        "errorCode": 0,
        "result": {
            "layoutParsingResults": [
                {"prunedResult": {}, "markdown": {"text": "page one"}},
                {"prunedResult": {}, "markdown": {"text": "page two"}},
            ]
        },
    }
    client = PaddleOcrClient(
        "http://ocr:8080",
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=response)),
    )

    with pytest.raises(PaddleOcrError, match="one page"):
        client.extract_markdown(b"\x89PNG\r\n\x1a\nscan")
