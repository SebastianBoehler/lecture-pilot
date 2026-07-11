from __future__ import annotations

import os
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from lecturepilot.session_auth import SESSION_COOKIE_NAME
from lecturepilot.session_store import SessionStoreError


SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
EXEMPT_PATHS = frozenset(
    {
        "/auth/login",
    }
)
DEFAULT_LOCAL_ORIGINS = (
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
)


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not _needs_check(request):
            return await call_next(request)
        origin = request.headers.get("origin", "").rstrip("/")
        if not origin or origin not in allowed_origins():
            return _forbidden("Request origin is not allowed.")
        fetch_site = request.headers.get("sec-fetch-site")
        if fetch_site and fetch_site not in {"same-origin", "same-site"}:
            return _forbidden("Cross-site state change is not allowed.")
        try:
            request.app.state.session_store.verify_csrf(
                request.cookies.get(SESSION_COOKIE_NAME, ""),
                request.headers.get("x-csrf-token"),
            )
        except SessionStoreError as exc:
            return _forbidden(str(exc))
        return await call_next(request)


def allowed_origins() -> tuple[str, ...]:
    configured = os.getenv("LECTUREPILOT_ALLOWED_ORIGINS", "").strip()
    if not configured:
        if _is_production():
            raise RuntimeError("LECTUREPILOT_ALLOWED_ORIGINS is required in production.")
        return DEFAULT_LOCAL_ORIGINS
    origins = tuple(
        origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()
    )
    return tuple(_validated_origin(origin, production=_is_production()) for origin in origins)


def _validated_origin(origin: str, *, production: bool) -> str:
    parsed = urlsplit(origin)
    if origin == "*" or parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("Allowed origins must be exact HTTP or HTTPS origins.")
    if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise RuntimeError("Allowed origins must not contain credentials, paths, or fragments.")
    if production and parsed.scheme != "https":
        raise RuntimeError("Production allowed origins must use HTTPS.")
    return origin


def _is_production() -> bool:
    return os.getenv("LECTUREPILOT_ENV", "").strip().lower() == "production"


def _needs_check(request: Request) -> bool:
    return (
        request.method.upper() not in SAFE_METHODS
        and request.url.path not in EXEMPT_PATHS
        and SESSION_COOKIE_NAME in request.cookies
        and not request.headers.get("authorization")
    )


def _forbidden(detail: str) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": detail})
