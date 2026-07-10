from fastapi.testclient import TestClient

from lecturepilot.app import create_app


def test_security_headers_are_applied() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.headers["content-security-policy"].startswith("default-src 'none'")
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "camera=()" in response.headers["permissions-policy"]


def test_openapi_and_docs_are_disabled_in_production(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_ENV", "production")
    monkeypatch.setenv("LECTUREPILOT_ALLOWED_HOSTS", "testserver")
    client = TestClient(create_app())

    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_request_body_limit_rejects_large_payload(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_MAX_REQUEST_BYTES", "20")
    client = TestClient(create_app())

    response = client.post("/auth/login", json={"username": "student01", "password": "x" * 50})

    assert response.status_code == 413
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "limited to 20 bytes" in response.text


def test_login_rate_limit_rejects_excess_requests(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_RATE_LIMIT_LOGIN_PER_MINUTE", "1")
    client = TestClient(create_app())

    first = client.post("/auth/login", json={"username": "student01", "password": "x"})
    second = client.post("/auth/login", json={"username": "student01", "password": "x"})

    assert first.status_code != 429
    assert second.status_code == 429
    assert second.headers["x-content-type-options"] == "nosniff"
    assert second.headers["retry-after"]
