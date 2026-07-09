from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException

from lecturepilot.api_auth import (
    request_context,
    require_course_manager,
    require_learner_workspace_access,
)
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.canvas_workspace import CanvasWorkspaceError
from lecturepilot.course_access import require_course_id_access, require_lecture_id_access
from lecturepilot.course_media import apply_course_media, course_media_evidence
from lecturepilot.learner_workspace_reset import (
    LearnerWorkspaceResetInput,
    LearnerWorkspaceResetResult,
    reset_learner_workspace,
)
from lecturepilot.learning_map import LearningMap, write_learning_map
from lecturepilot.models import CanvasPublicationResult, Course, Lecture
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.source_bundle_canvas import SourceBundleCanvasError
from lecturepilot.tenancy import TenantContext


def register_course_canvas_routes(
    app: FastAPI,
    *,
    course_tenant_id: str,
    lectures: list[Lecture],
    seeded_course: Course,
    source_document: Callable[[str, str], CanvasDocument],
) -> None:
    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/draft",
        response_model=CanvasDocument,
    )
    async def draft_course_canvas(
        course_id: str,
        lecture_id: str,
        context: TenantContext = Depends(request_context),
    ) -> CanvasDocument:
        try:
            require_course_manager(context, course_tenant_id=course_tenant_id)
            source = source_document(course_id, lecture_id)
            source = course_media_evidence(
                source, app.state.canvas_workspace.course_media_root(course_id)
            )
            document = await app.state.course_planner.plan_canvas(source)
            document = apply_course_media(
                document, app.state.canvas_workspace.course_media_root(course_id)
            )
            return app.state.canvas_workspace.write_course_canvas_draft(document)
        except CanvasWorkspaceError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except SourceBundleCanvasError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ProviderConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ModelExecutionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.get(
        "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/draft",
        response_model=CanvasDocument,
    )
    def preview_course_canvas_draft(
        course_id: str,
        lecture_id: str,
        context: TenantContext = Depends(request_context),
    ) -> CanvasDocument:
        try:
            require_course_manager(context, course_tenant_id=course_tenant_id)
            return app.state.canvas_workspace.read_course_canvas_draft(
                course_id=course_id,
                lecture_id=lecture_id,
            )
        except CanvasWorkspaceError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/canvas/publish",
        response_model=CanvasPublicationResult,
    )
    def publish_course_canvas_draft(
        course_id: str,
        lecture_id: str,
        context: TenantContext = Depends(request_context),
    ) -> CanvasPublicationResult:
        try:
            require_course_manager(context, course_tenant_id=course_tenant_id)
            metadata = app.state.canvas_workspace.publish_course_canvas_draft(
                course_id=course_id,
                lecture_id=lecture_id,
                published_by=context.user_id,
            )
            return _publication_result(course_id, lecture_id, metadata)
        except CanvasWorkspaceError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/courses/{course_id}/lectures/{lecture_id}/canvas/publication",
        response_model=CanvasPublicationResult,
    )
    def course_canvas_publication(
        course_id: str,
        lecture_id: str,
        context: TenantContext = Depends(request_context),
    ) -> CanvasPublicationResult:
        require_lecture_id_access(
            app,
            context,
            course_id=course_id,
            lecture_id=lecture_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=lectures,
        )
        if context.tenant_id != course_tenant_id:
            raise HTTPException(
                status_code=403, detail="Resource does not belong to the active tenant."
            )
        metadata = app.state.canvas_workspace.course_canvas_publication(
            course_id=course_id,
            lecture_id=lecture_id,
        )
        if metadata is None and app.state.canvas_workspace.has_published_course_canvas(
            course_id=course_id,
            lecture_id=lecture_id,
        ):
            metadata = {}
        return _publication_result(course_id, lecture_id, metadata)

    @app.get("/courses/{course_id}/lectures/{lecture_id}/canvas")
    def lecture_canvas(
        course_id: str,
        lecture_id: str,
        user_id: str,
        context: TenantContext = Depends(request_context),
    ) -> dict:
        require_learner_workspace_access(
            context,
            learner_user_id=user_id,
            course_tenant_id=course_tenant_id,
        )
        require_lecture_id_access(
            app,
            context,
            course_id=course_id,
            lecture_id=lecture_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=lectures,
        )
        if not app.state.canvas_workspace.has_published_course_canvas(
            course_id=course_id,
            lecture_id=lecture_id,
        ):
            raise HTTPException(status_code=404, detail="Canvas has not been published.")
        try:
            document = app.state.canvas_workspace.read_document(
                course_id=course_id,
                lecture_id=lecture_id,
                user_id=user_id,
            )
        except CanvasWorkspaceError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return document.model_dump()

    @app.get(
        "/courses/{course_id}/lectures/{lecture_id}/learning-map",
        response_model=LearningMap,
    )
    def lecture_learning_map(
        course_id: str,
        lecture_id: str,
        context: TenantContext = Depends(request_context),
    ) -> LearningMap:
        require_lecture_id_access(
            app,
            context,
            course_id=course_id,
            lecture_id=lecture_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
            seeded_lectures=lectures,
        )
        if not app.state.canvas_workspace.has_published_course_canvas(
            course_id=course_id,
            lecture_id=lecture_id,
        ):
            raise HTTPException(status_code=404, detail="Canvas has not been published.")
        canvas_dir = app.state.canvas_workspace.course_canvas_store.path(course_id, lecture_id)
        document = app.state.canvas_workspace.course_canvas_store.read(
            course_id=course_id,
            lecture_id=lecture_id,
            workspace_path=str(canvas_dir / "index.md"),
        )
        if document is None:
            raise HTTPException(status_code=404, detail="Canvas has not been published.")
        return write_learning_map(document, canvas_dir)

    @app.post(
        "/courses/{course_id}/learner-workspace/reset",
        response_model=LearnerWorkspaceResetResult,
    )
    def reset_course_learner_workspace(
        course_id: str,
        request: LearnerWorkspaceResetInput,
        context: TenantContext = Depends(request_context),
    ) -> LearnerWorkspaceResetResult:
        require_learner_workspace_access(
            context,
            learner_user_id=request.user_id,
            course_tenant_id=course_tenant_id,
        )
        require_course_id_access(
            app,
            context,
            course_id=course_id,
            course_tenant_id=course_tenant_id,
            seeded_course=seeded_course,
        )
        return reset_learner_workspace(
            layout=app.state.canvas_workspace.layout,
            course_id=course_id,
            request=request,
        )


def _publication_result(
    course_id: str,
    lecture_id: str,
    metadata: dict | None,
) -> CanvasPublicationResult:
    return CanvasPublicationResult(
        course_id=course_id,
        lecture_id=lecture_id,
        published=metadata is not None,
        version=metadata.get("version") if metadata else None,
        published_at=metadata.get("published_at") if metadata else None,
        published_by=metadata.get("published_by") if metadata else None,
        source_draft_path=metadata.get("source_draft_path") if metadata else None,
        published_path=metadata.get("published_path") if metadata else None,
    )
