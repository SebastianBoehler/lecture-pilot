from fastapi import FastAPI

from lecturepilot.course_canvas_context import InvalidPublishedCanvasContextError
from lecturepilot.metadata_events import emit_metadata_event


def published_canvas_is_ready(
    app: FastAPI,
    *,
    course_id: str,
    lecture_id: str,
    invalid_as_unavailable: bool = False,
) -> bool:
    try:
        return app.state.canvas_workspace.has_published_course_canvas(
            course_id=course_id,
            lecture_id=lecture_id,
        )
    except InvalidPublishedCanvasContextError as exc:
        if not invalid_as_unavailable:
            raise
        emit_metadata_event(
            "canvas.publication_invalid",
            error=True,
            course_id=course_id,
            lecture_id=lecture_id,
            exception_type=type(exc.__cause__ or exc).__name__,
        )
        return False
