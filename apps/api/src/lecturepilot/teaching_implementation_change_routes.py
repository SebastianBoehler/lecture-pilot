import json

from fastapi import Depends, HTTPException, Request

from lecturepilot.api_auth import request_context, require_course_manager
from lecturepilot.course_practice_design_store import PracticeDesignStore
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.tenancy import TenantContext


def register_implementation_change_routes(app, *, course_tenant_id):
    @app.get(
        "/admin/courses/{course_id}/lectures/{lecture_id}/practice-design/implementation-changes"
    )
    def changes(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
        require_course_manager(
            context, course_tenant_id=course_tenant_id, request=request, course_id=course_id
        )
        layout = app.state.canvas_workspace.layout
        with locked_course_state(layout.course_root(course_id)):
            design = PracticeDesignStore(layout).read(course_id=course_id, lecture_id=lecture_id)
            if design is None:
                raise HTTPException(404, "No teaching implementation exists.")
            path = layout.lecture_practice_design_path(course_id, lecture_id)
            report_path = (
                path.parent / path.stem / "implementation-changes" / f"{design.revision}.json"
            )
            if not report_path.exists():
                return {"report": None, "practice_design_revision": design.revision}
            report = json.loads(report_path.read_text())
            if (
                report["to_revision"] != design.revision
                or report["source_revision"] != design.source_revision
                or not design.learning_intent
                or report["learning_intent_revision"] != design.learning_intent.revision
            ):
                raise HTTPException(409, "Implementation report is no longer current.")
            return {"report": report, "practice_design_revision": design.revision}
