"""Connect owned generation requests to resumable teaching implementation jobs."""

from lecturepilot.teaching_recovery import continue_saved_implementation
from lecturepilot.course_learning_intent import digest
from lecturepilot.course_practice_design_planner import ReviewedPracticeDesignProposal
from lecturepilot.models import ProviderCapability
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
    initial_review=None,
):
    settings = planner.provider_registry.require_ready(
        [ProviderCapability.CHAT, ProviderCapability.STRUCTURED_JSON]
    )
    identity = digest(
        {
            "source": source_revision,
            "intent": protected_intent.revision,
            "initial": initial.model_dump(mode="json") if initial else None,
            "model": settings.model,
            "repair_context": repair_context,
            "initial_review": initial_review.model_dump(mode="json") if initial_review else None,
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
        initial_review=initial_review,
    )
    async with planner._model(settings, authorize=authorize) as model:
        authorize()
        proposal, reviewed = await run_teaching_design_job(job, model=model)
    return ReviewedPracticeDesignProposal(proposal, reviewed)


async def run_implementation_repair(**kwargs):
    return await continue_saved_implementation(_run_implementation_repair, **kwargs)
