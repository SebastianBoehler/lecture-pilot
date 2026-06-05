from __future__ import annotations

from datetime import date

from lecturepilot.models import Lecture


def is_lecture_unlocked(lecture: Lecture, *, today: date | None = None) -> bool:
    current_day = today or date.today()
    return lecture.date <= current_day

