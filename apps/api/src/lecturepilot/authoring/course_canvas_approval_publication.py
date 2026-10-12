"""Approve & publish: one professor action over one exact, reviewed draft."""

from pydantic import ValidationError

from lecturepilot.canvas.canvas_markdown import CanvasMarkdownError
from lecturepilot.authoring.course_canvas_publication import CanvasPublicationMetadata
from lecturepilot.canvas.course_canvas_store import InvalidCanvasDraftError
from lecturepilot.learning_design.course_learning_design_errors import LearningDesignError
from lecturepilot.learning_design.course_learning_design_models import LearningDesignApprovalInput
from lecturepilot.learning_design.course_learning_design_store import (
    CourseLearningDesignStore,
    review_path,
)
from lecturepilot.courses.course_update_recovery import locked_course_state
from lecturepilot.core.durable_files import atomic_write_text


def approve_and_publish(
    workspace,
    *,
    course_id: str,
    lecture_id: str,
    approval: LearningDesignApprovalInput,
    published_by: str,
) -> CanvasPublicationMetadata:
    """Approve the exact draft revisions the professor reviewed, then publish them.

    Both steps run under one course lock. A failed publication restores the previous
    review, so the action never leaves half of itself behind.
    """
    layout = workspace.layout
    path = review_path(layout.course_canvas_draft_dir(course_id, lecture_id))
    with locked_course_state(layout.course_root(course_id)):
        previous = path.read_text(encoding="utf-8") if path.exists() else None
        try:
            CourseLearningDesignStore(layout).approve(
                course_id=course_id,
                lecture_id=lecture_id,
                approval=approval,
                approved_by=published_by,
            )
        except LearningDesignError:
            raise
        except (CanvasMarkdownError, ValidationError, ValueError) as exc:
            raise InvalidCanvasDraftError(
                "Stored canvas draft is invalid. Retry generation for this lecture."
            ) from exc
        try:
            return workspace.publish_course_canvas_draft(
                course_id=course_id, lecture_id=lecture_id, published_by=published_by
            )
        except BaseException:
            if previous is not None:
                atomic_write_text(path, previous)
            raise
