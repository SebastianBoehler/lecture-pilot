from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


_ATTEMPT_ID = re.compile(r"^[a-f0-9]{32}$")
_PROVIDERS = {"alma", "ilias"}


@dataclass
class AuthHtmlCapture:
    attempt_id: str
    root: Path
    sequence: int = 0

    @classmethod
    def from_environment(cls, attempt_id: str) -> AuthHtmlCapture | None:
        if not _enabled():
            return None
        if _ATTEMPT_ID.fullmatch(attempt_id) is None:
            raise ValueError("Authentication capture requires a generated attempt id.")
        workspace_root = Path(os.getenv("LECTUREPILOT_WORKSPACE_ROOT", ".lecturepilot/workspaces"))
        return cls(attempt_id=attempt_id, root=workspace_root / "auth-diagnostics")

    def capture_response(self, provider: str, response: Any) -> dict[str, Any] | None:
        if provider not in _PROVIDERS:
            raise ValueError("Unsupported authentication capture provider.")
        html = getattr(response, "text", None)
        if not isinstance(html, str) or not _looks_like_html(response, html):
            return None

        self.sequence += 1
        status = getattr(response, "status_code", None)
        method = str(getattr(getattr(response, "request", None), "method", "response"))
        safe_method = re.sub(r"[^a-z0-9]+", "-", method.casefold()).strip("-") or "response"
        safe_status = str(status) if isinstance(status, int) else "unknown"
        filename = f"{self.sequence:03d}-{provider}-{safe_method}-{safe_status}.html"
        attempt_dir = self.root / self.attempt_id
        attempt_dir.mkdir(parents=True, exist_ok=True)
        destination = attempt_dir / filename
        destination.write_text(html, encoding="utf-8")

        details: dict[str, Any] = {
            "capture_bytes": len(html.encode("utf-8")),
            "capture_file": filename,
            "provider": provider,
        }
        if isinstance(status, int):
            details["http_status"] = status
        url = getattr(response, "url", None)
        if isinstance(url, str):
            parsed = urlparse(url)
            if parsed.hostname:
                details["response_host"] = parsed.hostname
            if parsed.path:
                details["response_path"] = parsed.path[:240]
        return details


def _enabled() -> bool:
    return os.getenv("LECTUREPILOT_AUTH_CAPTURE_HTML", "").strip().casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _looks_like_html(response: Any, content: str) -> bool:
    headers = getattr(response, "headers", {})
    content_type = str(headers.get("content-type", "")).casefold()
    if "html" in content_type:
        return True
    prefix = content.lstrip().casefold()[:80]
    return prefix.startswith(("<!doctype html", "<html", "<?xml"))
