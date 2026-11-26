from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints
from fastapi import Depends, FastAPI, HTTPException, Request

from lecturepilot.tutor.agent_annotation import require_annotation_access
from lecturepilot.identity.api_auth import request_context
from lecturepilot.canvas.canvas_annotations import AnnotationStore, CanvasAnnotation
from lecturepilot.courses.course_update_recovery import locked_course_state
from lecturepilot.courses.course_access import require_lecture_id_access
from lecturepilot.courses.professor_preview import resolve_learner_workspace_access
from lecturepilot.identity.tenancy import TenantContext


class LearnerAnnotationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    publication_version: int
    block_id: Annotated[str, StringConstraints(min_length=1, max_length=160)]
    comment: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


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

    @app.put(
        "/courses/{course_id}/lectures/{lecture_id}/annotations/{annotation_id}",
        response_model=CanvasAnnotation,
    )
    def save_annotation(
        course_id: str,
        lecture_id: str,
        annotation_id: UUID,
        payload: LearnerAnnotationInput,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
        access, store = authorized(request, context, course_id, lecture_id)
        workspace = app.state.canvas_workspace
        with locked_course_state(workspace.layout.course_root(course_id)):
            snapshot = workspace.read_published_canvas_view(
                user_id=access.user_id, course_id=course_id, lecture_id=lecture_id
            )
            if snapshot is None or snapshot.version != payload.publication_version:
                raise HTTPException(409, "The section changed. Reload the lecture to save a note.")
            try:
                return store.save(
                    snapshot.document,
                    snapshot.version,
                    f"recall-{annotation_id}",
                    {"block_id": payload.block_id, "comment": payload.comment},
                )
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc

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
