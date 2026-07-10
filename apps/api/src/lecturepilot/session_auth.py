from __future__ import annotations

from dataclasses import dataclass
import os


_LOCAL_ENVS = frozenset({"development", "local", "test"})
_DEV_AUTH_MODES = frozenset({"dev", "dev-headers"})
SESSION_COOKIE_NAME = "lecturepilot_session"


class SessionAuthError(PermissionError):
    pass


@dataclass(frozen=True)
class SessionAuthSettings:
    mode: str
    ttl_minutes: int
    cookie_secure: bool
    cookie_samesite: str

    @classmethod
    def from_env(cls) -> "SessionAuthSettings":
        environment = os.getenv("LECTUREPILOT_ENV", "").strip().lower()
        default_mode = "dev" if environment in _LOCAL_ENVS else "session"
        mode = os.getenv("LECTUREPILOT_AUTH_MODE", default_mode).strip().lower()
        if mode not in {"dev", "dev-headers", "session"}:
            raise SessionAuthError("LECTUREPILOT_AUTH_MODE must be dev, dev-headers, or session.")
        if mode in _DEV_AUTH_MODES and environment not in _LOCAL_ENVS:
            raise SessionAuthError(
                "Dev header auth requires LECTUREPILOT_ENV=development, local, or test."
            )
        try:
            ttl = int(os.getenv("LECTUREPILOT_SESSION_TTL_MINUTES", "480"))
        except ValueError as exc:
            raise SessionAuthError("LECTUREPILOT_SESSION_TTL_MINUTES must be an integer.") from exc
        if ttl < 1:
            raise SessionAuthError("LECTUREPILOT_SESSION_TTL_MINUTES must be positive.")
        same_site = os.getenv("LECTUREPILOT_SESSION_COOKIE_SAMESITE", "lax").lower()
        if same_site not in {"lax", "strict", "none"}:
            raise SessionAuthError("Session cookie SameSite must be lax, strict, or none.")
        return cls(
            mode=mode,
            ttl_minutes=ttl,
            cookie_secure=_bool_env(
                "LECTUREPILOT_SESSION_COOKIE_SECURE", environment == "production"
            ),
            cookie_samesite=same_site,
        )

    @property
    def allow_dev_headers(self) -> bool:
        return self.mode in _DEV_AUTH_MODES


def bearer_token(header: str | None) -> str | None:
    if not header:
        return None
    scheme, separator, token = header.partition(" ")
    if separator and scheme.casefold() == "bearer" and token:
        return token
    raise SessionAuthError("Bearer session token is malformed.")


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
