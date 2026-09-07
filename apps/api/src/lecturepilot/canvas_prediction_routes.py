from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.agent_annotation import require_annotation_access
from lecturepilot.api_auth import request_context
from lecturepilot.canvas_prediction_models import CanvasPrediction
from lecturepilot.canvas_predictions import PredictionStore
from lecturepilot.course_access import require_lecture_id_access
from lecturepilot.professor_preview import resolve_learner_workspace_access
from lecturepilot.tenancy import TenantContext


class PredictionSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    publication_version: int = Field(ge=1)
    block_id: str = Field(min_length=1, max_length=120)
    answer: str | None = Field(min_length=1, max_length=2000)


def register_canvas_prediction_routes(app: FastAPI, **seeded):
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
            raise HTTPException(
                409, "Predictions are closed during an independent attempt."
            ) from exc
        snapshot = workspace.read_published_canvas_view(
            user_id=access.user_id,
            course_id=course_id,
            lecture_id=lecture_id,
        )
        if snapshot is None:
            raise HTTPException(404, "Canvas has not been published.")
        return snapshot, PredictionStore(workspace.layout, access.user_id, course_id, lecture_id)

    @app.get(
        "/courses/{course_id}/lectures/{lecture_id}/predictions",
        response_model=list[CanvasPrediction],
    )
    def predictions(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
        snapshot, store = authorized(request, context, course_id, lecture_id)
        return store.list(snapshot.document, snapshot.version)

    @app.post(
        "/courses/{course_id}/lectures/{lecture_id}/predictions", response_model=CanvasPrediction
    )
    def save_prediction(
        course_id: str,
        lecture_id: str,
        body: PredictionSubmission,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
        snapshot, store = authorized(request, context, course_id, lecture_id)
        if body.publication_version != snapshot.version:
            raise HTTPException(409, "The lecture changed. Reload before saving your prediction.")
        try:
            return store.save(snapshot.document, snapshot.version, body.block_id, body.answer)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
