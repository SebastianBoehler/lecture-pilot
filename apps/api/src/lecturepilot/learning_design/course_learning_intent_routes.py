from typing import Annotated, Literal

from lecturepilot.learning_design.teaching_implementation_change_routes import (
    register_implementation_change_routes,
)

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, BeforeValidator, Field

from lecturepilot.identity.api_auth import request_context
from lecturepilot.learning_design.course_learning_intent_store import LearningIntentStore
from lecturepilot.learning_design.learning_goal_support import (
    goal_findings_path,
    goal_set_objective,
    read_goal_findings,
)
from lecturepilot.learning_design.course_learning_intent_proposal import LearningIntentProposal
from lecturepilot.learning_design.learning_goal_proposal_run import propose_lecture_goals
from lecturepilot.learning_design.learning_intent_keep_routes import (
    register_learning_intent_keep_route,
)
from lecturepilot.llm.model_client import ModelExecutionError
from lecturepilot.llm.providers import ProviderConfigurationError
from lecturepilot.learning_design.course_practice_design_contract import (
    StrictPracticeDesignModel,
    freeze_collection,
)
from lecturepilot.learning_design.course_practice_design_models import PracticeDesign
from lecturepilot.learning_design.course_practice_design_store import PracticeDesignStale
from lecturepilot.courses.course_update_recovery import locked_course_state
from lecturepilot.identity.tenancy import TenantContext


class GoalFinding(BaseModel):
    goal_id: str
    reason: str
    status: Literal["open", "repaired_unchecked"] = "open"


class LearningIntentApprovalInput(StrictPracticeDesignModel):
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    practice_design_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    fixed_target_ids: Annotated[tuple[str, ...], BeforeValidator(freeze_collection)] = Field(
        default_factory=tuple,
        max_length=8,
    )


class LearningIntentUpdate(LearningIntentProposal):
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    practice_design_revision: str = Field(pattern=r"^[a-f0-9]{64}$")


def register_learning_intent_routes(
    app, *, course_tenant_id, source_document, source_context, source_revision, require_manager
):
    register_implementation_change_routes(app, course_tenant_id=course_tenant_id)
    register_learning_intent_keep_route(
        app,
        course_tenant_id=course_tenant_id,
        source_document=source_document,
        source_context=source_context,
        source_revision=source_revision,
        require_manager=require_manager,
    )

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
                revision = source_revision(app, course_id, lecture_id)
                if revision != approval.source_revision:
                    raise PracticeDesignStale("Course sources changed. Review the current goals.")
                return LearningIntentStore(layout).approve(
                    course_id=course_id,
                    lecture_id=lecture_id,
                    source_revision=revision,
                    design_revision=approval.practice_design_revision,
                    approved_by=context.user_id,
                    fixed_target_ids=approval.fixed_target_ids,
                )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get(
        "/admin/courses/{course_id}/lectures/{lecture_id}/practice-design/intent/findings",
        response_model=list[GoalFinding],
    )
    def goal_findings(
        course_id: str,
        lecture_id: str,
        request: Request,
        context: TenantContext = Depends(request_context),
    ):
        require_manager(context, request, course_id, course_tenant_id)
        layout = app.state.canvas_workspace.layout
        design = LearningIntentStore(layout).read(course_id=course_id, lecture_id=lecture_id)
        if design is None:
            return []
        return read_goal_findings(
            goal_findings_path(layout, course_id, lecture_id), design.learning_intent.goals
        )

    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/practice-design/intent/proposal",
        response_model=PracticeDesign,
    )
    async def propose_goals(
        course_id: str,
        lecture_id: str,
        request: Request,
        refresh: bool = False,
        context: TenantContext = Depends(request_context),
    ):
        """Propose goals once per source revision; `refresh` replaces unapproved goals."""
        require_manager(context, request, course_id, course_tenant_id)
        try:
            return await propose_lecture_goals(
                app,
                course_id=course_id,
                lecture_id=lecture_id,
                actor_user_id=context.user_id,
                refresh=refresh,
                source_document=source_document,
                source_context=source_context,
                source_revision=source_revision,
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
            source, revision, paths = source_context(app, source_document, course_id, lecture_id)
            with locked_course_state(layout.course_root(course_id)):
                existing = store.read(course_id=course_id, lecture_id=lecture_id)
                if source_revision(app, course_id, lecture_id) != revision:
                    raise PracticeDesignStale("Learning goals or sources changed. Reload them.")
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
                    # The objective always promises exactly the edited goal set.
                    proposal=update.model_copy(
                        update={"objective": goal_set_objective(update.goals)}
                    ),
                    source=source,
                    allowed_source_paths=paths,
                )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
