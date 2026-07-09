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
                if _hsts_enabled():
                    _setdefault(headers, "Strict-Transport-Security", "max-age=31536000")
            await send(message)

        await self.app(scope, receive, add_headers)


def production_fastapi_kwargs() -> dict[str, str | None]:
    if os.getenv("LECTUREPILOT_ENV", "").strip().lower() != "production":
        return {}
    return {"docs_url": None, "redoc_url": None, "openapi_url": None}


def _setdefault(headers: MutableHeaders, name: str, value: str) -> None:
    if name not in headers:
        headers[name] = value


def _hsts_enabled() -> bool:
    return os.getenv("LECTUREPILOT_HSTS_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
