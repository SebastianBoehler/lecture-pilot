import asyncio
import json
from lecturepilot.authoring_limits import (
    authoring_budget,
    AuthoringBudgetExceeded,
    AUTHORING_DEADLINE_SECONDS,
)

"""Connect owned generation requests to resumable teaching implementation jobs."""

from lecturepilot.course_learning_intent import digest
from lecturepilot.course_practice_design_planner import ReviewedPracticeDesignProposal
from lecturepilot.models import ProviderCapability
from lecturepilot.authoring_models import AuthoringDesignConflict
from lecturepilot.learning_goal_scope_review import (
    LearningGoalScopeReview,
    review_learning_goal_scope,
    scope_review_instructions,
    scope_review_settings,
)
from lecturepilot.durable_files import atomic_write_json
from lecturepilot.practice_evidence_catalogue import evidence_catalogue
from lecturepilot.teaching_design_job import TeachingDesignJob, run_teaching_design_job


async def _run_implementation_repair(
    *,
    planner,
    root,
    authorize,
    source,
    source_revision,
    allowed_source_paths,
    initial,
    protected_intent,
    repair_context,
):
    settings = planner.provider_registry.require_ready(
        [ProviderCapability.CHAT, ProviderCapability.TOOL_CALLS, ProviderCapability.STRUCTURED_JSON]
    )
    identity = digest(
        {
            "source": source_revision,
            "intent": protected_intent.revision,
            "initial": initial.model_dump(mode="json") if initial else None,
            "model": settings.model,
            "repair_context": repair_context,
        }
    )

    async def review(proposal):
        return await planner.review(
            source=source,
            source_revision=source_revision,
            allowed_source_paths=allowed_source_paths,
            proposal=proposal,
            settings=settings,
        )

    job = TeachingDesignJob(
        root=root / identity,
        source=source,
        intent=protected_intent,
        initial=initial,
        paths=tuple(allowed_source_paths),
        source_revision=source_revision,
        settings=settings,
        review=review,
        authorize=authorize,
        repair_context=repair_context,
    )
    async with planner._model(settings, authorize=authorize) as model:
        authorize()
        catalogue = evidence_catalogue(source, allowed_source_paths)
        scope_key = digest(
            {
                "intent": protected_intent.revision,
                "evidence": catalogue,
                "model": settings.model,
                "instructions": scope_review_instructions(),
                "settings": scope_review_settings(settings),
            }
        )
        scope_path = root / identity / "scope-review.json"
        saved = json.loads(scope_path.read_text()) if scope_path.exists() else None
        if saved is not None and saved.get("identity") == scope_key:
            scope = LearningGoalScopeReview.model_validate(saved["review"])
        else:
            scope = await review_learning_goal_scope(
                model=model,
                settings=settings,
                proposal=protected_intent,
                catalogue=catalogue,
            )
            authorize()
            if scope.coherent:
                atomic_write_json(
                    scope_path, {"identity": scope_key, "review": scope.model_dump(mode="json")}
                )
        authorize()
        if not scope.coherent:
            raise AuthoringDesignConflict(
                "The approved learning goals do not match the lecture objective. "
                "Review and edit the learning plan, then approve its new revision: " + scope.reason
            )
        proposal, reviewed = await run_teaching_design_job(job, model=model)
    return ReviewedPracticeDesignProposal(proposal, reviewed)


async def run_implementation_repair(**kwargs):
    with authoring_budget():
        try:
            async with asyncio.timeout(AUTHORING_DEADLINE_SECONDS):
                return await _run_implementation_repair(**kwargs)
        except TimeoutError as exc:
            raise AuthoringBudgetExceeded(
                "Teaching implementation deadline reached; saved targets can resume."
            ) from exc
