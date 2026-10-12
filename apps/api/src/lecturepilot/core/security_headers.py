from __future__ import annotations

import os

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Scope, Send


API_CSP = "default-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def add_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                _setdefault(headers, "Content-Security-Policy", API_CSP)
                _setdefault(headers, "Referrer-Policy", "no-referrer")
                _setdefault(headers, "X-Content-Type-Options", "nosniff")
                _setdefault(headers, "X-Frame-Options", "DENY")
                _setdefault(
                    headers, "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
                )
                if hsts_enabled():
                    _setdefault(headers, "Strict-Transport-Security", "max-age=31536000")
            await send(message)

        await self.app(scope, receive, add_headers)


def production_fastapi_kwargs() -> dict[str, str | None]:
    if os.getenv("LECTUREPILOT_ENV", "").strip().lower() != "production":
        return {}
    return {"docs_url": None, "redoc_url": None, "openapi_url": None}


def allowed_hosts() -> list[str]:
    configured = os.getenv("LECTUREPILOT_ALLOWED_HOSTS", "").strip()
    if configured:
        hosts = [host.strip() for host in configured.split(",") if host.strip()]
        if _is_production() and any(not _is_exact_hostname(host) for host in hosts):
            raise RuntimeError(
                "LECTUREPILOT_ALLOWED_HOSTS must contain exact hostnames in production."
            )
        return hosts
    if _is_production():
        raise RuntimeError("LECTUREPILOT_ALLOWED_HOSTS is required in production.")
    return ["localhost", "127.0.0.1", "testserver"]


def _setdefault(headers: MutableHeaders, name: str, value: str) -> None:
    if name not in headers:
        headers[name] = value


def hsts_enabled() -> bool:
    configured = os.getenv("LECTUREPILOT_HSTS_ENABLED")
    if configured is None or not configured.strip():
        return _is_production()
    return configured.strip().lower() in {"1", "true", "yes", "on"}


def _is_exact_hostname(host: str) -> bool:
    return bool(host) and not any(
        marker in host for marker in ("*", "://", "/", "\\", "?", "#", "@", " ")
    )


def _is_production() -> bool:
    return os.getenv("LECTUREPILOT_ENV", "").strip().lower() == "production"
