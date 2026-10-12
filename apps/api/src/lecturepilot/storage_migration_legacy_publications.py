"""Report legacy publications; they cannot be migrated without the professor recreating them.

Legacy publication metadata lacks the source, draft and learning-map revisions that bind a
published canvas. ``course_legacy_publication`` keeps such lectures unavailable to learners and
offers owners only deletion. This report lists them so the operator knows when that code can be
removed (an empty list on every deployment). ``apply`` is accepted for a uniform migration
interface but never changes anything.
"""

from __future__ import annotations

from pathlib import Path

from lecturepilot.course_legacy_publication import is_legacy_publication


def migrate(storage_root: Path, *, apply: bool = False) -> dict:
    legacy = []
    for metadata in sorted(
        (storage_root / "courses").glob("*/*/canvas/lectures/*/publication.json")
    ):
        published_dir = metadata.parent
        if is_legacy_publication(published_dir):
            course_root = published_dir.parent.parent.parent
            legacy.append(
                {
                    "tenant": course_root.parent.name,
                    "course_id": course_root.name,
                    "lecture_id": published_dir.name,
                }
            )
    return {
        "migration": "legacy_publications",
        "applied": False,
        "report_only": True,
        "legacy_publications": legacy,
    }
