from __future__ import annotations

import re
from pathlib import Path


LECTURE_FILE_RE = re.compile(r"(?:^|[/_-])lecture[-_ ]?0*(\d{1,2})(?:\D|$)", re.IGNORECASE)


def lecture_source_candidates(
    *,
    lecture_id: str,
    uploads_dir: Path,
    uploaded_sources: list[Path],
    configured_source: str | None,
) -> list[Path]:
    candidates: list[Path] = []
    if configured_source:
        candidates.append(uploads_dir / configured_source)
        candidates.extend(path for path in uploaded_sources if path.name == configured_source)

    if lecture_number := _lecture_number(lecture_id):
        candidates.extend(
            path
            for path in sorted(uploaded_sources, key=_source_priority)
            if _lecture_number(path.name) == lecture_number
        )

    candidates.extend(sorted(uploaded_sources))
    return list(dict.fromkeys(candidates))


def _lecture_number(value: str) -> int | None:
    match = LECTURE_FILE_RE.search(value)
    return int(match.group(1)) if match else None


def _source_priority(path: Path) -> tuple[int, int, str]:
    lowered = path.name.casefold()
    language_bonus = -2 if "-eng" in lowered else 0
    return (language_bonus, len(path.name), str(path))
