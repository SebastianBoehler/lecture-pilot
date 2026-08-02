from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from lecturepilot.session_cookie import attach_session_cookie


class SessionCookieRefreshMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        token = getattr(request.state, "session_cookie_refresh_token", None)
        if token:
            attach_session_cookie(response, token)
        return response
