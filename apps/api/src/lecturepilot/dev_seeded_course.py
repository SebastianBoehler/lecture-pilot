from __future__ import annotations

from datetime import date
from pathlib import Path

from lecturepilot.canvas_workspace_config import SEEDED_COURSE_ID, default_material_root
from lecturepilot.lecture_schedule import propose_lecture_schedule
from lecturepilot.models import AttendanceStatus, Lecture, LectureView
from lecturepilot.source_bundle import scan_source_bundle


SEEDED_COURSE_START_DATE = date(2026, 5, 6)


def discovered_seeded_lecture_views(course_id: str, material_root: Path | None = None) -> list[LectureView]:
    if course_id != SEEDED_COURSE_ID:
        return []
    root = material_root or default_material_root()
    if not root.exists() or not root.is_dir():
        return []
    proposal = propose_lecture_schedule(
        course_id=course_id,
        files=scan_source_bundle(root),
        roots=[root],
        first_lecture_date=SEEDED_COURSE_START_DATE,
    )
    if len(proposal.lectures) <= 3:
        return []
    return [
        LectureView(
            lecture=Lecture(
                id=f"lecture-{int(item.number):02d}",
                course_id=course_id,
                title=item.title,
                date=item.date,
                material_path=item.material_path,
            ),
            unlocked=True,
            attendance=AttendanceStatus.UNKNOWN,
        )
        for item in proposal.lectures
    ]
