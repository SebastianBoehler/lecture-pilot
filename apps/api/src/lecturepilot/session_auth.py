from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
import binascii
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import os

from lecturepilot.models import TenantRole, TuebingenLoginResult
from lecturepilot.tenancy import TenantContext


_LOCAL_ENVS = frozenset({"development", "local", "test"})
_DEV_AUTH_MODES = frozenset({"dev", "dev-headers"})


class SessionAuthError(PermissionError):
    """Raised when an auth token is missing, malformed, expired, or invalid."""


@dataclass(frozen=True)
class SessionAuthSettings:
    mode: str
    secret: str
    ttl_minutes: int

    @classmethod
    def from_env(cls) -> "SessionAuthSettings":
        env = os.getenv("LECTUREPILOT_ENV", "").strip().lower()
        default_mode = "dev" if env in _LOCAL_ENVS else "session"
        mode = os.getenv("LECTUREPILOT_AUTH_MODE", default_mode).strip().lower()
        if mode not in {"dev", "dev-headers", "session"}:
            raise SessionAuthError("LECTUREPILOT_AUTH_MODE must be dev, dev-headers, or session.")
        if mode in _DEV_AUTH_MODES and env not in _LOCAL_ENVS:
            raise SessionAuthError(
                "Dev header auth requires LECTUREPILOT_ENV=development, local, or test."
            )
        secret = os.getenv("LECTUREPILOT_SESSION_SECRET")
        if not secret:
            if mode == "session":
                raise SessionAuthError("LECTUREPILOT_SESSION_SECRET is required for session auth.")
            secret = "lecturepilot-local-dev-session-secret"
        try:
            ttl = int(os.getenv("LECTUREPILOT_SESSION_TTL_MINUTES", "480"))
        except ValueError as exc:
            raise SessionAuthError("LECTUREPILOT_SESSION_TTL_MINUTES must be an integer.") from exc
        if ttl < 1:
            raise SessionAuthError("LECTUREPILOT_SESSION_TTL_MINUTES must be positive.")
        return cls(mode=mode, secret=secret, ttl_minutes=ttl)

    @property
    def allow_dev_headers(self) -> bool:
        return self.mode in {"dev", "dev-headers"}


def sign_session(context: TenantContext, *, settings: SessionAuthSettings | None = None) -> str:
    settings = settings or SessionAuthSettings.from_env()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.ttl_minutes)
    payload = {
        "course_ids": sorted(context.course_ids),
        "exp": int(expires_at.timestamp()),
        "roles": sorted(role.value for role in context.roles),
        "tenant_id": context.tenant_id,
        "user_id": context.user_id,
    }
    body = _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _signature(body, settings.secret)
    return f"{body}.{signature}"


def with_access_token(result: TuebingenLoginResult) -> TuebingenLoginResult:
    context = TenantContext(
        tenant_id=result.tenant_id,
        user_id=result.username,
        roles=frozenset(result.roles),
        course_ids=frozenset(course.id for course in result.courses),
    )
    return result.model_copy(update={"access_token": sign_session(context)})


def context_from_bearer_token(header: str | None) -> TenantContext:
    if not header:
        raise SessionAuthError("Authentication is required.")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise SessionAuthError("Bearer session token is required.")
    return verify_session_token(token)


def verify_session_token(
    token: str, *, settings: SessionAuthSettings | None = None
) -> TenantContext:
    settings = settings or SessionAuthSettings.from_env()
    body, separator, signature = token.partition(".")
    if not separator or not body or not signature:
        raise SessionAuthError("Session token is malformed.")
    expected = _signature(body, settings.secret)
    if not hmac.compare_digest(signature, expected):
        raise SessionAuthError("Session token signature is invalid.")
    try:
        payload = json.loads(urlsafe_b64decode(_pad(body)).decode("utf-8"))
        expires_at = int(payload["exp"])
        roles = frozenset(TenantRole(role) for role in payload["roles"])
        tenant_id = str(payload["tenant_id"]).strip()
        user_id = str(payload["user_id"]).strip()
        course_ids = frozenset(
            str(course_id).strip() for course_id in payload.get("course_ids", [])
        )
    except (
        binascii.Error,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        raise SessionAuthError("Session token payload is invalid.") from exc
    if expires_at < int(datetime.now(UTC).timestamp()):
        raise SessionAuthError("Session token has expired.")
    if not tenant_id or not user_id or not roles:
        raise SessionAuthError("Session token is incomplete.")
    return TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        roles=roles,
        course_ids=frozenset(course_id for course_id in course_ids if course_id),
    )


def _signature(body: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return _b64(digest)


def _b64(payload: bytes) -> str:
    return urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _pad(payload: str) -> bytes:
    return (payload + "=" * (-len(payload) % 4)).encode("ascii")
