from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from lecturepilot.lecture_schedule import propose_lecture_schedule
from lecturepilot.models import LectureScheduleItem, LectureScheduleProposal
from lecturepilot.source_bundle import SourceBundleFile


def complete_source_schedule(
    proposal: LectureScheduleProposal,
    *,
    course_id: str,
    files: list[SourceBundleFile],
    roots: list[Path],
    first_lecture_date: date | None,
    requested_count: int | None,
) -> LectureScheduleProposal:
    deterministic = propose_lecture_schedule(
        course_id=course_id,
        files=files,
        roots=roots,
        first_lecture_date=first_lecture_date,
        requested_count=requested_count,
    )
    if not deterministic.lectures:
        return proposal

    by_path = {
        lecture.material_path: lecture
        for lecture in proposal.lectures
        if lecture.material_path is not None
    }
    by_number = {_lecture_key(lecture.number): lecture for lecture in proposal.lectures}
    merged = [_merge_lecture(lecture, by_path, by_number) for lecture in deterministic.lectures]
    return LectureScheduleProposal(
        course_id=course_id,
        lectures=merged,
        source_paths=[lecture.material_path for lecture in merged if lecture.material_path],
    )


def _merge_lecture(
    detected: LectureScheduleItem,
    by_path: dict[str, LectureScheduleItem],
    by_number: dict[str, LectureScheduleItem],
) -> LectureScheduleItem:
    model_lecture = by_path.get(detected.material_path or "")
    if model_lecture is None:
        numbered = by_number.get(_lecture_key(detected.number))
        if numbered and numbered.material_path in {None, detected.material_path}:
            model_lecture = numbered
    if model_lecture is None:
        return detected
    return LectureScheduleItem(
        number=detected.number,
        title=model_lecture.title,
        date=detected.date,
        material_path=detected.material_path,
    )


def _lecture_key(number: str) -> str:
    digits = re.sub(r"\D+", "", number)
    return str(int(digits)) if digits else number.strip().casefold()
