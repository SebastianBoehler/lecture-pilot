from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from lecturepilot.api_auth import request_context
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_practice_design_models import (
    PracticeDesign,
    PracticeDesignApprovalInput,
    PracticeDesignProposal,
)
from lecturepilot.course_practice_design_store import PracticeDesignStale, PracticeDesignStore
from lecturepilot.course_practice_design_validation import PracticeDesignValidationError
from lecturepilot.course_practice_design_route_context import _source_revision as source_revision
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.tenancy import TenantContext


SourceContext = Callable[
    [FastAPI, Callable[[str, str], CanvasDocument], str, str],
    tuple[CanvasDocument, str, tuple[str, ...]],
]
ManagerCheck = Callable[[TenantContext, Request, str, str], None]


def register_practice_design_review_route(
    app: FastAPI,
    *,
    course_tenant_id: str,
    source_document: Callable[[str, str], CanvasDocument],
    source_context: SourceContext,
    require_manager: ManagerCheck,
) -> None:
    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/practice-design/review",
        response_model=PracticeDesign,
    )
    async def review_practice_design(
        course_id: str,
        lecture_id: str,
        requested: PracticeDesignApprovalInput,
        request: Request,
        context: TenantContext = Depends(request_context),
    ) -> PracticeDesign:
        require_manager(context, request, course_id, course_tenant_id)
        layout = app.state.canvas_workspace.layout
        store = PracticeDesignStore(layout)

        def load():
            # Parse without the course lock; the lock only guards the saved design.
            loaded = source_context(app, source_document, course_id, lecture_id)
            with locked_course_state(layout.course_root(course_id)):
                return loaded, store.read(course_id=course_id, lecture_id=lecture_id)

        (source, revision, paths), current = await run_in_threadpool(load)
        if current is None:
            raise HTTPException(status_code=404, detail="Practice design has not been proposed.")
        if (
            requested.source_revision != revision
            or requested.practice_design_revision != current.revision
        ):
            raise HTTPException(
                status_code=409,
                detail="The practice design or source revision changed. Reload it.",
            )
        expected_review = current.quality_review
        expected_approval = current.approval
        proposal = PracticeDesignProposal(
            lecture_title=current.lecture_title,
            objective=current.objective,
            planning_context=current.planning_context,
            targets=current.targets,
        )
        try:
            with model_usage_scope(
                actor_user_id=context.user_id,
                course_id=course_id,
                workload="course_practice_design_review",
            ):
                review = await app.state.practice_design_planner.review(
                    source=source,
                    source_revision=revision,
                    allowed_source_paths=paths,
                    proposal=proposal,
                )
        except ProviderConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ModelExecutionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        def save() -> PracticeDesign:
            with locked_course_state(layout.course_root(course_id)):
                # Same revision means the same confirmed files, so the parsed source still holds.
                if source_revision(app, course_id, lecture_id) != revision:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "Course sources changed while the learning plan was reviewed. "
                            "Review it again."
                        ),
                    )
                try:
                    return store.save_review(
                        course_id=course_id,
                        lecture_id=lecture_id,
                        source_revision=revision,
                        design_revision=requested.practice_design_revision,
                        review=review,
                        source=source,
                        allowed_source_paths=paths,
                        expected_design_review=expected_review,
                        expected_design_approval=expected_approval,
                    )
                except PracticeDesignStale as exc:
                    raise HTTPException(status_code=409, detail=str(exc)) from exc
                except PracticeDesignValidationError as exc:
                    raise HTTPException(status_code=502, detail=str(exc)) from exc

        return await run_in_threadpool(save)
