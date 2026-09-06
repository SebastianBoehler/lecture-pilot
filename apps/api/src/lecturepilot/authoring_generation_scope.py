from lecturepilot.authoring_runtime import AuthoringScope
from lecturepilot.course_canvas_generation_ownership import require_generation_ownership
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.course_practice_design_store import PracticeDesignStore
from lecturepilot.course_canvas_store import InvalidCanvasDraftError
from lecturepilot.authoring_session import bind_session
from lecturepilot.authoring_status import authoring_metrics_path
from lecturepilot.durable_files import atomic_write_json


def generation_authoring_scope(
    app, *, ownership, source_revision, session_generation_id=None, candidate=None
):
    layout = app.state.canvas_workspace.layout

    def authorize():
        require_generation_ownership(layout, ownership)
        revision = lecture_source_revision(
            layout, course_id=ownership.course_id, lecture_id=ownership.lecture_id
        )
        if revision != source_revision:
            raise InvalidCanvasDraftError(
                "Course sources changed during authoring. Generate this draft again."
            )
        PracticeDesignStore(layout).require_approved(
            course_id=ownership.course_id,
            lecture_id=ownership.lecture_id,
            source_revision=source_revision,
            design_revision=ownership.practice_design_revision,
        )

    root = bind_session(layout, ownership, session_generation_id)
    design = PracticeDesignStore(layout).read(
        course_id=ownership.course_id, lecture_id=ownership.lecture_id
    )
    if design is not None and design.learning_intent is not None:
        root = root / "implementations" / ownership.practice_design_revision
    return AuthoringScope(
        root=root,
        source_revision=source_revision,
        authorize=authorize,
        candidate=candidate,
        report=lambda metrics: atomic_write_json(
            authoring_metrics_path(
                layout,
                ownership.course_id,
                ownership.lecture_id,
                ownership.generation_id,
            ),
            metrics.model_dump(mode="json"),
        ),
    )
