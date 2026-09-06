import json

from lecturepilot.agent_side_effect_tools import AgentSideEffectError
from lecturepilot.canvas_annotations import AnnotationStore
from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.models import CanvasCommand


def require_annotation_access(layout, user_id, course_id, lecture_id):
    progress = CoachingProgressStore(layout).read(
        user_id=user_id,
        course_id=course_id,
        lecture_id=lecture_id,
    )
    if progress.pending_check and progress.pending_check.stage in {
        "independent_exit",
        "delayed_transfer",
    }:
        raise ValueError(
            "Annotations are closed during an independent attempt. Request help first."
        )


def write_annotation(executor, logical_path, content, *, expected_text=None):
    filename = logical_path.removeprefix("/lecture/annotations/")
    if "/" in filename or not filename.endswith(".json"):
        raise AgentSideEffectError("Use /lecture/annotations/<name>.json for a comment.")
    if len(content.encode("utf-8")) > 12000:
        raise AgentSideEffectError("Annotation file exceeds 12000 bytes.")
    workspace = executor.canvas_workspace
    try:
        require_annotation_access(
            workspace.layout, executor.user_id, executor.course_id, executor.lecture_id
        )
        snapshot = workspace.read_published_canvas_view(
            user_id=executor.user_id,
            course_id=executor.course_id,
            lecture_id=executor.lecture_id,
        )
        if snapshot is None:
            raise ValueError("Canvas has not been published.")
        note = AnnotationStore(
            workspace.layout, executor.user_id, executor.course_id, executor.lecture_id
        ).save(
            snapshot.document,
            snapshot.version,
            filename[:-5],
            json.loads(content),
            expected_text=expected_text,
        )
    except ValueError as exc:
        raise AgentSideEffectError(str(exc)) from exc
    executor.focus_section_id = note.section_id
    executor.highlight_command = CanvasCommand(
        type="highlight_span",
        section_id=note.section_id,
        span_id=note.block_id,
        highlight_text=note.quote[:160] or None,
    )
    return {
        "path": logical_path,
        "annotation_id": note.id,
        "block_id": note.block_id,
        "saved": True,
    }
