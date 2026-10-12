from __future__ import annotations

import hashlib
import json


def canonical_json_digest(payload: object) -> str:
    """SHA-256 of sorted, compact, ASCII-escaped JSON; stored revisions depend on these bytes."""
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
