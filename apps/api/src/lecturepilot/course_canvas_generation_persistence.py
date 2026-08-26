from fastapi import FastAPI

from lecturepilot import course_canvas_generation_ownership as ownership_store
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.course_canvas_store import InvalidCanvasDraftError
from lecturepilot.course_practice_design_store import (
    PracticeDesignApprovalRequired,
    PracticeDesignStale,
    PracticeDesignStore,
)
from lecturepilot.course_update_recovery import locked_course_state


def write_current_draft(
    app: FastAPI,
    document: CanvasDocument,
    *,
    expected_source_revision: str,
    ownership: ownership_store.CanvasGenerationOwnership,
) -> CanvasDocument:
    course_root = app.state.canvas_workspace.course_media_root(document.course_id)
    with locked_course_state(course_root):
        current_source_revision = lecture_source_revision(
            app.state.canvas_workspace.layout,
            course_id=document.course_id,
            lecture_id=document.lecture_id,
        )
        if current_source_revision != expected_source_revision:
            raise InvalidCanvasDraftError(
                "Course sources changed during generation. Generate this draft again."
            )
        try:
            ownership_store.require_generation_ownership(
                app.state.canvas_workspace.layout, ownership
            )
        except ownership_store.CanvasGenerationOwnershipError as exc:
            raise InvalidCanvasDraftError(str(exc)) from exc
        try:
            practice_design = PracticeDesignStore(
                app.state.canvas_workspace.layout
            ).require_approved(
                course_id=document.course_id,
                lecture_id=document.lecture_id,
                source_revision=expected_source_revision,
                design_revision=ownership.practice_design_revision,
            )
        except (PracticeDesignApprovalRequired, PracticeDesignStale) as exc:
            raise InvalidCanvasDraftError(
                "The practice design changed during generation. Generate this draft again."
            ) from exc
        return app.state.canvas_workspace.write_course_canvas_draft(
            document,
            expected_source_revision=expected_source_revision,
            practice_design=practice_design,
        )
