import pytest
from fastapi.testclient import TestClient

from lecturepilot.app import create_app
from lecturepilot.csrf import allowed_origins
from lecturepilot.database import DatabaseConfigurationError, DatabaseSettings
from lecturepilot.production_preflight import validate_production_environment
from lecturepilot.security_headers import allowed_hosts, hsts_enabled, production_fastapi_kwargs
from lecturepilot.session_auth import SessionAuthError, SessionAuthSettings


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

    assert production_fastapi_kwargs() == {
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None,
    }


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


def test_professor_login_uses_the_login_rate_limit(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_RATE_LIMIT_LOGIN_PER_MINUTE", "1")
    client = TestClient(create_app())

    first = client.post(
        "/auth/professor/login",
        json={"email": "professor@example.edu", "password": "invalid password value"},
    )
    second = client.post(
        "/auth/professor/login",
        json={"email": "professor@example.edu", "password": "invalid password value"},
    )

    assert first.status_code != 429
    assert second.status_code == 429


def test_production_rejects_an_insecure_session_cookie(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_ENV", "production")
    monkeypatch.setenv("LECTUREPILOT_AUTH_MODE", "session")
    monkeypatch.setenv("LECTUREPILOT_SESSION_COOKIE_SECURE", "false")

    with pytest.raises(SessionAuthError, match="Secure session cookies"):
        create_app()


def test_local_http_keeps_secure_cookie_disabled_by_default(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_ENV", "development")
    monkeypatch.delenv("LECTUREPILOT_SESSION_COOKIE_SECURE", raising=False)

    assert SessionAuthSettings.from_env().cookie_secure is False


def test_production_requires_explicit_https_origins(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_ENV", "production")
    monkeypatch.delenv("LECTUREPILOT_ALLOWED_ORIGINS", raising=False)

    with pytest.raises(RuntimeError, match="ALLOWED_ORIGINS is required"):
        allowed_origins()

    monkeypatch.setenv("LECTUREPILOT_ALLOWED_ORIGINS", "http://lecturepilot.example.edu")
    with pytest.raises(RuntimeError, match="must use HTTPS"):
        allowed_origins()

    monkeypatch.setenv("LECTUREPILOT_ALLOWED_ORIGINS", "https://lecturepilot.example.edu")
    assert allowed_origins() == ("https://lecturepilot.example.edu",)


def test_production_rejects_wildcard_hosts(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_ENV", "production")
    monkeypatch.setenv("LECTUREPILOT_ALLOWED_HOSTS", "*")

    with pytest.raises(RuntimeError, match="exact hostnames"):
        allowed_hosts()


def test_production_requires_postgresql(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///lecturepilot.db")

    with pytest.raises(DatabaseConfigurationError, match="PostgreSQL"):
        DatabaseSettings.from_env()


def test_hsts_defaults_on_only_in_production(monkeypatch) -> None:
    monkeypatch.setenv("LECTUREPILOT_ENV", "production")
    monkeypatch.delenv("LECTUREPILOT_HSTS_ENABLED", raising=False)
    assert hsts_enabled() is True

    monkeypatch.setenv("LECTUREPILOT_ENV", "development")
    assert hsts_enabled() is False


def test_production_preflight_accepts_complete_configuration() -> None:
    configured = {
        "LECTUREPILOT_DOMAIN": "lecturepilot.example.edu",
        "LECTUREPILOT_POSTGRES_PASSWORD": "safe_url_token_0123456789abcdef",
        "LECTUREPILOT_MODEL": "gemini/gemini-3.1-flash-lite",
        "LECTUREPILOT_ALLOWED_MODELS": "gemini/gemini-3.1-flash-lite",
        "GEMINI_API_KEY": "configured-outside-the-repository",
        "LECTUREPILOT_TRACE_CONTENT": "metadata",
    }

    assert validate_production_environment(configured) == []


def test_production_preflight_names_missing_settings_without_echoing_values() -> None:
    configured = {
        "LECTUREPILOT_DOMAIN": "localhost",
        "LECTUREPILOT_POSTGRES_PASSWORD": "do-not-echo-this",
        "LECTUREPILOT_MODEL": "gemini/gemini-3.1-flash-lite",
        "LECTUREPILOT_ALLOWED_MODELS": "openai/gpt-5",
        "LECTUREPILOT_TRACE_CONTENT": "full",
    }

    errors = " ".join(validate_production_environment(configured))

    assert "LECTUREPILOT_DOMAIN" in errors
    assert "LECTUREPILOT_POSTGRES_PASSWORD" in errors
    assert "LECTUREPILOT_ALLOWED_MODELS" in errors
    assert "GEMINI_API_KEY" in errors
    assert "LECTUREPILOT_TRACE_CONTENT" in errors
    assert "do-not-echo-this" not in errors


def test_production_preflight_rejects_invalid_dns_labels() -> None:
    configured = {
        "LECTUREPILOT_DOMAIN": "lecturepilot.example.-edu",
        "LECTUREPILOT_POSTGRES_PASSWORD": "safe_url_token_0123456789abcdef",
        "LECTUREPILOT_MODEL": "gemini/gemini-3.1-flash-lite",
        "LECTUREPILOT_ALLOWED_MODELS": "gemini/gemini-3.1-flash-lite",
        "GEMINI_API_KEY": "configured-outside-the-repository",
    }

    assert any(
        "LECTUREPILOT_DOMAIN" in error
        for error in validate_production_environment(configured)
    )
