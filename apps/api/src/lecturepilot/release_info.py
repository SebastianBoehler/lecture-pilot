from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
import re


_PACKAGE_NAME = "lecturepilot-api"
_COMMIT_SHA = re.compile(r"^[0-9a-fA-F]{7,64}$")
_BUILD_COMMIT_PATH = Path(__file__).with_name("_build_commit.txt")


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    version: str
    commit_sha: str


def release_info() -> ReleaseInfo:
    return ReleaseInfo(
        version=_installed_version(),
        commit_sha=_build_commit_sha(),
    )


def _installed_version() -> str:
    try:
        return package_version(_PACKAGE_NAME)
    except PackageNotFoundError:
        return "unknown"


def _build_commit_sha() -> str:
    try:
        value = _BUILD_COMMIT_PATH.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        return "unknown"
    return value.lower() if _COMMIT_SHA.fullmatch(value) else "unknown"
