from fastapi import FastAPI

from lecturepilot.canvas.course_canvas_context import InvalidPublishedCanvasContextError


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
    except InvalidPublishedCanvasContextError:
        # The workspace reports an invalid snapshot once, when it validates it.
        if not invalid_as_unavailable:
            raise
        return False
