from __future__ import annotations

from pathlib import PurePosixPath

PROJECT_METADATA_NAMES = {"pyproject.toml"}


def is_project_metadata(value: str) -> bool:
    return PurePosixPath(value).name.casefold() in PROJECT_METADATA_NAMES
