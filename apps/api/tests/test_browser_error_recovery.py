from fastapi.testclient import TestClient

from lecturepilot.app import create_app


ORIGIN = "http://127.0.0.1:5173"


def test_browser_can_read_rate_limit_error_and_retry_timing(monkeypatch):
    monkeypatch.setenv("LECTUREPILOT_RATE_LIMIT_LOGIN_PER_MINUTE", "1")
    client = TestClient(create_app())
    client.post("/auth/login", headers={"Origin": ORIGIN}, json={})
    response = client.post("/auth/login", headers={"Origin": ORIGIN}, json={})
    assert response.status_code == 429
    assert response.headers.get("access-control-allow-origin") == ORIGIN
    assert "Retry-After" in response.headers["access-control-expose-headers"]


def test_browser_can_read_repairable_generation_metadata():
    response = TestClient(create_app()).get("/health", headers={"Origin": ORIGIN})
    assert "X-Generation-Repairable" in response.headers["access-control-expose-headers"]


def test_reading_drafts_does_not_consume_paid_generation_quota(monkeypatch):
    monkeypatch.setenv("LECTUREPILOT_RATE_LIMIT_PAID_PER_MINUTE", "1")
    client = TestClient(create_app())
    for _ in range(3):
        response = client.get("/admin/courses/martius-ml/lectures/lecture-01/canvas/draft")
        assert response.status_code != 429
