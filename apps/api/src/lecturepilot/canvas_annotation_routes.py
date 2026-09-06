from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.agent_annotation import require_annotation_access
from lecturepilot.api_auth import request_context
from lecturepilot.canvas_annotations import AnnotationStore, CanvasAnnotation
from lecturepilot.course_access import require_lecture_id_access
from lecturepilot.professor_preview import resolve_learner_workspace_access
from lecturepilot.tenancy import TenantContext


def register_canvas_annotation_routes(app: FastAPI, **seeded):
    def authorized(request, context, course_id, lecture_id):
        access = resolve_learner_workspace_access(
            request,
            context,
            course_id=course_id,
            course_tenant_id=seeded["course_tenant_id"],
        )
        require_lecture_id_access(
            app, context, course_id=course_id, lecture_id=lecture_id, **seeded
        )
        workspace = app.state.canvas_workspace
        try:
            require_annotation_access(workspace.layout, access.user_id, course_id, lecture_id)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return access, AnnotationStore(workspace.layout, access.user_id, course_id, lecture_id)

    @app.get(
        "/courses/{course_id}/lectures/{lecture_id}/annotations",
        response_model=list[CanvasAnnotation],
    )
    def annotations(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
        access, store = authorized(request, context, course_id, lecture_id)
        snapshot = app.state.canvas_workspace.read_published_canvas_view(
            user_id=access.user_id,
            course_id=course_id,
            lecture_id=lecture_id,
        )
        if snapshot is None:
            raise HTTPException(404, "Canvas has not been published.")
        return store.list(snapshot.document, snapshot.version)

    @app.delete("/courses/{course_id}/lectures/{lecture_id}/annotations/{annotation_id}")
    def delete_annotation(
        course_id: str,
        lecture_id: str,
        annotation_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
        _, store = authorized(request, context, course_id, lecture_id)
        try:
            store.delete(annotation_id)
        except FileNotFoundError as exc:
            raise HTTPException(404, "Annotation not found.") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"deleted": True}
