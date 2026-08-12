from __future__ import annotations

from pathlib import Path

from lecturepilot.course_canvas_generation_jobs import CanvasGenerationJob
from lecturepilot.storage_layout import StorageLayout, safe_id


def find_latest_canvas_generation(
    layout: StorageLayout,
    *,
    course_id: str,
    lecture_id: str,
    actor_user_id: str,
) -> CanvasGenerationJob | None:
    """Return the newest durable generation record for this professor and lecture."""
    actor_key = layout.user_key(actor_user_id)
    directory = layout.course_root(course_id) / "builder" / "generations" / safe_id(lecture_id)
    generations = [
        job
        for path in directory.glob("*.json")
        if (job := _read_job(path)) is not None and job.actor_key == actor_key
    ]
    return max(generations, key=lambda job: job.updated_at, default=None)


def find_latest_canvas_failure(
    layout: StorageLayout,
    *,
    course_id: str,
    lecture_id: str,
    actor_user_id: str,
    repairable_only: bool = False,
) -> CanvasGenerationJob | None:
    """Return the newest durable failure for this professor and lecture."""
    actor_key = layout.user_key(actor_user_id)
    directory = layout.course_root(course_id) / "builder" / "generations" / safe_id(lecture_id)
    failures = [
        job
        for path in directory.glob("*.json")
        if (job := _read_job(path)) is not None
        and job.status == "failed"
        and job.actor_key == actor_key
        and (not repairable_only or job.error_code == "canvas_generation_repairable_error")
    ]
    return max(failures, key=lambda job: job.updated_at, default=None)


def _read_job(path: Path) -> CanvasGenerationJob | None:
    try:
        return CanvasGenerationJob.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
