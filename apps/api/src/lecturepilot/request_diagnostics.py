from __future__ import annotations

from secrets import token_hex
from time import perf_counter

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from lecturepilot.metadata_events import emit_metadata_event, request_scope


_QUIET_PROBES = frozenset({"/health", "/ready"})


class RequestDiagnosticsMiddleware:
    """Emit metadata-only request lifecycle events with server-generated ids."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = token_hex(16)
        method = str(scope.get("method", "UNKNOWN"))[:16].upper()
        probe = scope.get("path") in _QUIET_PROBES
        status_code = 500
        started_at = perf_counter()

        async def send_with_diagnostics(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        with request_scope(request_id):
            if not probe:
                emit_metadata_event("http.request_started", method=method)
            try:
                await self.app(scope, receive, send_with_diagnostics)
            except BaseException as exc:
                _emit_finished(scope, method, status_code, started_at, type(exc).__name__)
                raise
            if not probe or status_code >= 400:
                _emit_finished(scope, method, status_code, started_at)


def _emit_finished(
    scope: Scope,
    method: str,
    status_code: int,
    started_at: float,
    exception_type: str | None = None,
) -> None:
    route = scope.get("route")
    route_path = getattr(route, "path", "<unmatched>")
    emit_metadata_event(
        "http.request_finished",
        error=status_code >= 500 or exception_type is not None,
        exception_type=exception_type,
        latency_ms=round((perf_counter() - started_at) * 1000, 3),
        method=method,
        route=route_path,
        status_code=status_code,
    )
