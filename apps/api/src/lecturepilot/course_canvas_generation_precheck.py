"""Fast precheck before queuing canvas generation; heavy parsing runs inside the job."""

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool

from lecturepilot import course_canvas_generation_ownership as ownership_store
from lecturepilot.course_builder_source import course_builder_source_revision
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.course_practice_design_store import (
    PracticeDesignApprovalRequired,
    PracticeDesignStale,
    PracticeDesignUnavailable,
)
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError


async def require_current_practice_design(
    app: FastAPI,
    course_id: str,
    lecture_id: str,
    *,
    expected_source_revision: str | None = None,
    expected_practice_design_revision: str | None = None,
) -> PracticeDesign:
    # Hashing files and taking the course lock block; keep both off the event loop.
    def check() -> PracticeDesign:
        return ownership_store.require_generation_practice_design(
            app.state.canvas_workspace.layout,
            lambda course, lecture: course_builder_source_revision(app, course, lecture),
            course_id=course_id,
            lecture_id=lecture_id,
            expected_source_revision=expected_source_revision,
            expected_practice_design_revision=expected_practice_design_revision,
        )

    try:
        return await run_in_threadpool(check)
    except (
        ownership_store.CanvasGenerationOwnershipError,
        PracticeDesignApprovalRequired,
        PracticeDesignStale,
        PracticeDesignUnavailable,
        SourceBundleCanvasError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
