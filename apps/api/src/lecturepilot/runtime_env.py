from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_project_env() -> None:
    if os.getenv("LECTUREPILOT_ENV", "").strip().casefold() == "production":
        return
    env_path = _nearest_local_env(Path.cwd()) or _nearest_local_env(Path(__file__).resolve())
    if env_path:
        load_dotenv(env_path, override=False)


def _nearest_local_env(start: Path) -> Path | None:
    root = start if start.is_dir() else start.parent
    for path in (root, *root.parents):
        candidate = path / ".env.local"
        if candidate.is_file():
            return candidate
    return None
