from __future__ import annotations

import os
from dataclasses import dataclass

from starlette.types import ASGIApp, Message, Receive, Scope, Send


DEFAULT_MAX_REQUEST_BYTES = 600 * 1024 * 1024


@dataclass(frozen=True)
class RequestBodyLimitSettings:
    max_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES

    @classmethod
    def from_env(cls) -> "RequestBodyLimitSettings":
        return cls(
            max_request_bytes=_int_env("LECTUREPILOT_MAX_REQUEST_BYTES", DEFAULT_MAX_REQUEST_BYTES)
        )


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, settings: RequestBodyLimitSettings | None = None) -> None:
        self.app = app
        self.settings = settings or RequestBodyLimitSettings.from_env()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if _content_length(scope) > self.settings.max_request_bytes:
            await _send_413(send, self.settings.max_request_bytes)
            return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.settings.max_request_bytes:
                    raise RequestBodyTooLarge
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except RequestBodyTooLarge:
            if not response_started:
                await _send_413(send, self.settings.max_request_bytes)


class RequestBodyTooLarge(Exception):
    pass


async def _send_413(send: Send, max_bytes: int) -> None:
    body = f"Request body is limited to {max_bytes} bytes.".encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _content_length(scope: Scope) -> int:
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            try:
                return int(value.decode("ascii"))
            except ValueError:
                return 0
    return 0


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(1, value)
