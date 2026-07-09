from __future__ import annotations

from fastapi import Response

from lecturepilot.models import TuebingenLoginResult
from lecturepilot.session_auth import (
    SESSION_COOKIE_NAME,
    SessionAuthSettings,
    session_token_for_login,
    without_access_token,
)


def attach_session_cookie(response: Response, result: TuebingenLoginResult) -> TuebingenLoginResult:
    settings = SessionAuthSettings.from_env()
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_token_for_login(result),
        httponly=True,
        max_age=settings.ttl_minutes * 60,
        path="/",
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
    )
    return without_access_token(result)


def clear_session_cookie(response: Response) -> dict[str, bool]:
    settings = SessionAuthSettings.from_env()
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        httponly=True,
        path="/",
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
    )
    return {"ok": True}
