from __future__ import annotations

from lecturepilot.canvas_models import CanvasBlock


def canonical_quiz_id(block: CanvasBlock) -> str:
    return block.component_id or block.id


def is_quiz_block(block: CanvasBlock) -> bool:
    return block.type == "quiz" or (
        block.type == "component" and block.component_type == "single_choice_quiz"
    )


def published_canvas_version(workspace, *, course_id: str, lecture_id: str) -> int:
    publication = workspace.course_canvas_publication(
        course_id=course_id,
        lecture_id=lecture_id,
    )
    version = publication.get("version") if isinstance(publication, dict) else None
    return version if isinstance(version, int) and version >= 1 else 1
