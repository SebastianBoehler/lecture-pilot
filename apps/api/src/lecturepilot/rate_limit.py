from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from threading import Lock
import time

from starlette.types import ASGIApp, Scope, Send


@dataclass(frozen=True)
class RateLimit:
    name: str
    limit: int
    window_seconds: int


@dataclass
class RateBucket:
    count: int
    reset_at: float


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp, rules: dict[str, RateLimit] | None = None) -> None:
        self.app = app
        self.rules = rules or _rules_from_env()
        self.buckets: dict[tuple[str, str], RateBucket] = {}
        self.lock = Lock()
        self.enabled = os.getenv("LECTUREPILOT_RATE_LIMIT_ENABLED", "true").lower() not in {
            "0",
            "false",
            "no",
            "off",
        }

    async def __call__(self, scope: Scope, receive, send: Send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return
        rule = _rule_for(scope, self.rules)
        if rule is None:
            await self.app(scope, receive, send)
            return
        allowed, retry_after = self._consume(rule, _client_key(scope))
        if not allowed:
            await _send_429(send, retry_after)
            return
        await self.app(scope, receive, send)

    def _consume(self, rule: RateLimit, client_key: str) -> tuple[bool, int]:
        now = time.monotonic()
        key = (rule.name, client_key)
        with self.lock:
            bucket = self.buckets.get(key)
            if bucket is None or bucket.reset_at <= now:
                self.buckets[key] = RateBucket(count=1, reset_at=now + rule.window_seconds)
                self._prune(now)
                return True, rule.window_seconds
            if bucket.count >= rule.limit:
                return False, max(1, int(bucket.reset_at - now))
            bucket.count += 1
            return True, max(1, int(bucket.reset_at - now))

    def _prune(self, now: float) -> None:
        expired = [key for key, bucket in self.buckets.items() if bucket.reset_at <= now]
        for key in expired:
            self.buckets.pop(key, None)


def _rules_from_env() -> dict[str, RateLimit]:
    return {
        "login": RateLimit(
            name="login",
            limit=_int_env("LECTUREPILOT_RATE_LIMIT_LOGIN_PER_MINUTE", 30),
            window_seconds=60,
        ),
        "chat": RateLimit(
            name="chat",
            limit=_int_env("LECTUREPILOT_RATE_LIMIT_CHAT_PER_MINUTE", 120),
            window_seconds=60,
        ),
        "paid": RateLimit(
            name="paid",
            limit=_int_env("LECTUREPILOT_RATE_LIMIT_PAID_PER_MINUTE", 60),
            window_seconds=60,
        ),
    }


def _rule_for(scope: Scope, rules: dict[str, RateLimit]) -> RateLimit | None:
    method = str(scope.get("method", "")).upper()
    path = str(scope.get("path", ""))
    if method == "POST" and path == "/auth/login":
        return rules["login"]
    if method == "POST" and path in {"/agent/turn", "/agent/turn/stream"}:
        return rules["chat"]
    if method in {"GET", "POST"} and (
        path.endswith("/canvas/draft")
        or path.endswith("/lecture-schedule")
        or path.endswith("/exam-readiness")
        or path.endswith("/exam-readiness/attempts")
        or path.endswith("/media/youtube/search")
    ):
        return rules["paid"]
    return None


def _client_key(scope: Scope) -> str:
    headers = dict(scope.get("headers", []))
    auth_material = headers.get(b"authorization") or headers.get(b"cookie")
    if auth_material:
        return hashlib.sha256(auth_material).hexdigest()
    client = scope.get("client")
    return str(client[0] if client else "unknown")


async def _send_429(send: Send, retry_after: int) -> None:
    body = b"Rate limit exceeded."
    await send(
        {
            "type": "http.response.start",
            "status": 429,
            "headers": [
                (b"content-type", b"text/plain; charset=utf-8"),
                (b"content-length", str(len(body)).encode("ascii")),
                (b"retry-after", str(retry_after).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(1, value)
