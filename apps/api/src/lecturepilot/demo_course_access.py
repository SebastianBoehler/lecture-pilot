from __future__ import annotations

import os
import re
from pathlib import Path

from lecturepilot.course_schedule_store import list_course_workspaces
from lecturepilot.account_models import TuebingenLoginResult
from lecturepilot.models import Course

DEMO_CREATED_COURSES_FLAG = "LECTUREPILOT_DEMO_INCLUDE_CREATED_COURSES"


def include_created_courses_for_demo(
    result: TuebingenLoginResult,
    *,
    tenant_id: str,
    workspace_root: Path,
) -> TuebingenLoginResult:
    if not _enabled():
        return result
    created_courses = [
        workspace.course for workspace in list_course_workspaces(workspace_root, tenant_id)
    ]
    merged_courses = _merge_courses(result.courses, created_courses)
    if len(merged_courses) == len(result.courses):
        return result
    return result.model_copy(update={"courses": merged_courses})


def _merge_courses(enrolled: list[Course], created: list[Course]) -> list[Course]:
    merged = list(enrolled)
    seen_ids = {course.id for course in merged}
    seen_titles = {_normalized_title(course.title) for course in merged}
    for course in created:
        normalized_title = _normalized_title(course.title)
        if course.id in seen_ids or normalized_title in seen_titles:
            continue
        merged.append(course)
        seen_ids.add(course.id)
        seen_titles.add(normalized_title)
    return merged


def _enabled() -> bool:
    value = os.getenv(DEMO_CREATED_COURSES_FLAG, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _normalized_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.casefold()).strip()
