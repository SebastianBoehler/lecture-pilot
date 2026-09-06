from typing import Annotated

from lecturepilot.teaching_implementation_change_routes import register_implementation_change_routes

from fastapi import Depends, HTTPException, Request
from pydantic import BeforeValidator, Field

from lecturepilot.api_auth import request_context
from lecturepilot.course_learning_intent_store import LearningIntentStore
from lecturepilot.course_learning_intent_proposal import (
    LearningIntentProposal,
    propose_learning_intent,
)
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.course_practice_design_contract import freeze_collection
from lecturepilot.course_practice_design_models import PracticeDesign, PracticeDesignApprovalInput
from lecturepilot.course_practice_design_store import PracticeDesignStale
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.tenancy import TenantContext


class LearningIntentApprovalInput(PracticeDesignApprovalInput):
    fixed_target_ids: Annotated[tuple[str, ...], BeforeValidator(freeze_collection)] = Field(
        default_factory=tuple,
        max_length=8,
    )
    convert_legacy: bool = False


class LearningIntentUpdate(LearningIntentProposal):
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    practice_design_revision: str = Field(pattern=r"^[a-f0-9]{64}$")


def register_learning_intent_routes(
    app, *, course_tenant_id, source_document, source_context, require_manager
):
    register_implementation_change_routes(app, course_tenant_id=course_tenant_id)

    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/practice-design/intent/approve",
        response_model=PracticeDesign,
    )
    def approve_learning_intent(
        course_id: str,
        lecture_id: str,
        approval: LearningIntentApprovalInput,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
        require_manager(context, request, course_id, course_tenant_id)
        layout = app.state.canvas_workspace.layout
        try:
            with locked_course_state(layout.course_root(course_id)):
                _, revision, _ = source_context(app, source_document, course_id, lecture_id)
                if revision != approval.source_revision:
                    raise PracticeDesignStale("Course sources changed. Review the current goals.")
                return LearningIntentStore(layout).approve(
                    course_id=course_id,
                    lecture_id=lecture_id,
                    source_revision=revision,
                    design_revision=approval.practice_design_revision,
                    approved_by=context.user_id,
                    fixed_target_ids=approval.fixed_target_ids,
                    convert_legacy=approval.convert_legacy,
                )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/practice-design/intent/proposal",
        response_model=PracticeDesign,
    )
    async def propose_goals(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
        require_manager(context, request, course_id, course_tenant_id)
        layout = app.state.canvas_workspace.layout
        store = LearningIntentStore(layout)
        with locked_course_state(layout.course_root(course_id)):
            source, revision, paths = source_context(app, source_document, course_id, lecture_id)
            existing = store.read(course_id=course_id, lecture_id=lecture_id)
            if existing is not None and existing.source_revision == revision:
                return existing
        try:
            with model_usage_scope(
                actor_user_id=context.user_id,
                course_id=course_id,
                workload="course_learning_intent",
            ):
                proposal = await propose_learning_intent(
                    app.state.practice_design_planner,
                    source=source,
                    source_revision=revision,
                    allowed_source_paths=paths,
                )
            with locked_course_state(layout.course_root(course_id)):
                source, current, paths = source_context(app, source_document, course_id, lecture_id)
                if current != revision:
                    raise PracticeDesignStale("Course sources changed while goals were proposed.")
                return store.save_goals(
                    expected=existing,
                    course_id=course_id,
                    lecture_id=lecture_id,
                    source_revision=revision,
                    proposal=proposal,
                    source=source,
                    allowed_source_paths=paths,
                )
        except ProviderConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ModelExecutionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.put(
        "/admin/courses/{course_id}/lectures/{lecture_id}/practice-design/intent",
        response_model=PracticeDesign,
    )
    def update_goals(
        course_id: str,
        lecture_id: str,
        update: LearningIntentUpdate,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
        require_manager(context, request, course_id, course_tenant_id)
        layout = app.state.canvas_workspace.layout
        store = LearningIntentStore(layout)
        try:
            with locked_course_state(layout.course_root(course_id)):
                source, revision, paths = source_context(
                    app, source_document, course_id, lecture_id
                )
                existing = store.read(course_id=course_id, lecture_id=lecture_id)
                if (
                    existing is None
                    or existing.revision != update.practice_design_revision
                    or revision != update.source_revision
                ):
                    raise PracticeDesignStale("Learning goals or sources changed. Reload them.")
                return store.save_goals(
                    expected=existing,
                    course_id=course_id,
                    lecture_id=lecture_id,
                    source_revision=revision,
                    proposal=update,
                    source=source,
                    allowed_source_paths=paths,
                )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
