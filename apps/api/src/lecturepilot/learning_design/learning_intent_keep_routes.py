from fastapi import Depends, HTTPException, Request

from lecturepilot.courses.course_update_recovery import locked_course_state
from lecturepilot.identity.api_auth import request_context
from lecturepilot.identity.tenancy import TenantContext
from lecturepilot.learning_design.course_practice_design_models import PracticeDesign
from lecturepilot.learning_design.course_practice_design_store import (
    PracticeDesignStale,
    PracticeDesignStore,
)
from lecturepilot.learning_design.learning_intent_keep import (
    keep_learning_intent,
    require_keepable,
)


def register_learning_intent_keep_route(
    app, *, course_tenant_id, source_document, source_context, source_revision, require_manager
):
    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/practice-design/intent/keep",
        response_model=PracticeDesign,
    )
    def keep_learning_goals(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
        """Re-approve the same goals for changed sources as an explicit professor approval."""
        require_manager(context, request, course_id, course_tenant_id)
        layout = app.state.canvas_workspace.layout
        store = PracticeDesignStore(layout)
        try:
            with locked_course_state(layout.course_root(course_id)):
                revision = source_revision(app, course_id, lecture_id)
                expected = store.read(course_id=course_id, lecture_id=lecture_id)
            require_keepable(expected, revision)  # Cheap check before parsing sources.
            # Parsing (conversion, LaTeX, OCR) never holds the course lock.
            source, parsed_revision, paths = source_context(
                app, source_document, course_id, lecture_id
            )
            with locked_course_state(layout.course_root(course_id)):
                if source_revision(app, course_id, lecture_id) != parsed_revision:
                    raise PracticeDesignStale("Course sources changed. Reload the goals.")
                return keep_learning_intent(
                    layout,
                    expected=expected,
                    source_revision=parsed_revision,
                    approved_by=context.user_id,
                    source=source,
                    allowed_source_paths=paths,
                )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
