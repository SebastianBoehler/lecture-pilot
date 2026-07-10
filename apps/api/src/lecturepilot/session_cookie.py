from __future__ import annotations

from fastapi import Response

from lecturepilot.session_auth import SESSION_COOKIE_NAME, SessionAuthSettings


def attach_session_cookie(response: Response, token: str) -> None:
    settings = SessionAuthSettings.from_env()
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.ttl_minutes * 60,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    settings = SessionAuthSettings.from_env()
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
