"""Professor-requested AI proposal for a lecture's practice design (learning plan)."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from lecturepilot.api_auth import request_context
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_practice_design_models import PracticeDesign, PracticeDesignProposal
from lecturepilot.course_practice_design_route_context import (
    _require_manager,
    _source_context,
    _source_revision,
)
from lecturepilot.course_practice_design_store import (
    PracticeDesignStale,
    PracticeDesignStore,
    PracticeDesignUnavailable,
)
from lecturepilot.course_practice_design_validation import PracticeDesignValidationError
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_usage import model_usage_scope
from lecturepilot.providers import ProviderConfigurationError
from lecturepilot.tenancy import TenantContext


def register_practice_design_proposal_route(
    app: FastAPI,
    *,
    course_tenant_id: str,
    source_document: Callable[[str, str], CanvasDocument],
) -> None:
    @app.post(
        "/admin/courses/{course_id}/lectures/{lecture_id}/practice-design/proposal",
        response_model=PracticeDesign,
    )
    async def propose_practice_design(
        course_id: str,
        lecture_id: str,
        request: Request,
        refresh: bool = False,
        context: TenantContext = Depends(request_context),
    ) -> PracticeDesign:
        _require_manager(context, request, course_id, course_tenant_id)
        layout = app.state.canvas_workspace.layout
        store = _store(app)

        def load():
            # Parse without the course lock; the lock only guards the saved design.
            loaded = _source_context(app, source_document, course_id, lecture_id)
            with locked_course_state(layout.course_root(course_id)):
                return loaded, store.snapshot(course_id=course_id, lecture_id=lecture_id)

        try:
            (source, revision, paths), snapshot = await run_in_threadpool(load)
        except PracticeDesignUnavailable as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        existing = snapshot.design
        if not refresh and existing is not None and existing.source_revision == revision:
            return existing
        if (
            existing is not None
            and existing.approval is not None
            and existing.source_revision == revision
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "This plan is approved in full. Explicitly convert to learning-goal approval "
                    "before asking AI to change its protected teaching details."
                ),
            )
        expected_design_revision = existing.revision if existing is not None else None
        expected_design_approval = existing.approval if existing is not None else None
        expected_design_review = existing.quality_review if existing is not None else None
        try:
            with app.state.observability.tool_span(
                "course_practice_design",
                course_id=course_id,
                lecture_id=lecture_id,
                source_count=len(paths),
                workload="course_practice_design",
            ) as span:
                with model_usage_scope(
                    actor_user_id=context.user_id,
                    course_id=course_id,
                    workload="course_practice_design",
                ):
                    initial = (
                        PracticeDesignProposal(
                            lecture_title=existing.lecture_title,
                            objective=existing.objective,
                            planning_context=existing.planning_context,
                            targets=existing.targets,
                        )
                        if existing is not None
                        and existing.targets
                        and existing.source_revision == revision
                        else None
                    )
                    reviewed = await app.state.practice_design_planner.propose(
                        source=source,
                        source_revision=revision,
                        allowed_source_paths=paths,
                        **({"initial": initial} if initial is not None else {}),
                        **(
                            {
                                "protected_intent": existing.learning_intent,
                                "root": layout.course_root(course_id)
                                / "builder"
                                / "implementation-jobs"
                                / lecture_id,
                            }
                            if existing
                            and existing.learning_intent
                            and existing.learning_intent.approval
                            else {}
                        ),
                    )
                span.set_outputs({"target_count": len(reviewed.proposal.targets)})
        except ProviderConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ModelExecutionError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        def save() -> PracticeDesign:
            with locked_course_state(layout.course_root(course_id)):
                # Same revision means the same confirmed files, so the parsed source still holds.
                if _source_revision(app, course_id, lecture_id) != revision:
                    raise HTTPException(
                        status_code=409,
                        detail="Course sources changed while the learning plan was proposed. Generate a new proposal.",
                    )
                try:
                    return store.save_proposal(
                        course_id=course_id,
                        lecture_id=lecture_id,
                        source_revision=revision,
                        proposal=reviewed.proposal,
                        review=reviewed.review,
                        source=source,
                        allowed_source_paths=paths,
                        expected_design_revision=expected_design_revision,
                        expected_design_approval=expected_design_approval,
                        expected_design_review=expected_design_review,
                        expected_invalid_digest=snapshot.invalid_digest,
                        expected_learning_intent=existing.learning_intent if existing else None,
                        goals_first=existing is None or existing.learning_intent is not None,
                    )
                except PracticeDesignStale as exc:
                    raise HTTPException(status_code=409, detail=str(exc)) from exc
                except PracticeDesignUnavailable as exc:
                    raise HTTPException(status_code=500, detail=str(exc)) from exc
                except PracticeDesignValidationError as exc:
                    raise HTTPException(status_code=502, detail=str(exc)) from exc

        return await run_in_threadpool(save)


def _store(app: FastAPI) -> PracticeDesignStore:
    return PracticeDesignStore(app.state.canvas_workspace.layout)
