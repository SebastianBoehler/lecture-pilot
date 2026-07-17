from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.metadata_events import LOGGER_NAME
from auth_helpers import student_headers


def test_request_logs_use_route_templates_and_omit_urls(caplog) -> None:
    client = TestClient(create_app())

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        response = client.get(
            "/courses/private-course-name/lectures?secret=private-value",
            headers=student_headers(),
        )

    assert response.headers["x-request-id"]
    events = [json.loads(record.message) for record in caplog.records]
    assert [event["event"] for event in events] == [
        "http.request_started",
        "http.request_finished",
    ]
    assert events[-1]["route"] == "/courses/{course_id}/lectures"
    assert events[-1]["method"] == "GET"
    assert events[-1]["status_code"] == response.status_code
    assert events[-1]["latency_ms"] >= 0
    messages = "\n".join(record.message for record in caplog.records)
    assert "private-course-name" not in messages
    assert "private-value" not in messages


def test_successful_liveness_probe_is_quiet_but_failure_is_logged(monkeypatch, caplog) -> None:
    client = TestClient(create_app())

    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        response = client.get("/health")

    assert response.status_code == 200
    assert caplog.records == []

    monkeypatch.setenv("LECTUREPILOT_COMMIT_SHA", "bbbbbbbbbbbb")
    with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
        response = client.get("/health")

    assert response.status_code == 503
    event = json.loads(caplog.records[-1].message)
    assert event["event"] == "http.request_finished"
    assert event["route"] == "/health"
    assert event["status_code"] == 503


def test_canvas_generation_headers_are_available_to_the_local_browser() -> None:
    client = TestClient(create_app())
    origin = "http://127.0.0.1:5173"

    preflight = client.options(
        "/admin/courses/course-1/lectures/lecture-01/canvas/draft",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": ("idempotency-key,x-lecturepilot-client-contract"),
        },
    )
    response = client.get("/health", headers={"Origin": origin})

    assert preflight.status_code == 200
    assert "idempotency-key" in preflight.headers["access-control-allow-headers"].lower()
    assert (
        "x-lecturepilot-client-contract"
        in preflight.headers["access-control-allow-headers"].lower()
    )
    exposed = response.headers["access-control-expose-headers"].lower()
    assert "x-generation-id" in exposed
    assert "x-generation-status" in exposed
