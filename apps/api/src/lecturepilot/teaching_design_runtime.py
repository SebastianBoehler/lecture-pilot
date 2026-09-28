"""Connect owned generation requests to resumable teaching implementation jobs."""

from lecturepilot.course_learning_intent import digest
from lecturepilot.course_practice_design_planner import ReviewedPracticeDesignProposal
from lecturepilot.models import ProviderCapability
from lecturepilot.authoring_models import AuthoringDesignConflict
from lecturepilot.learning_goal_scope_review import review_learning_goal_scope
from lecturepilot.practice_evidence_catalogue import evidence_catalogue
from lecturepilot.teaching_design_job import TeachingDesignJob, run_teaching_design_job


async def run_implementation_repair(
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
        scope = await review_learning_goal_scope(
            model=model,
            settings=settings,
            proposal=protected_intent,
            catalogue=evidence_catalogue(source, allowed_source_paths),
        )
        authorize()
        if not scope.coherent:
            raise AuthoringDesignConflict(
                "The approved learning goals do not match the lecture objective. "
                "Review and edit the learning plan, then approve its new revision: " + scope.reason
            )
        proposal, reviewed = await run_teaching_design_job(job, model=model)
    return ReviewedPracticeDesignProposal(proposal, reviewed)
