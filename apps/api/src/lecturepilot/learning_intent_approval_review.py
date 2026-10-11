"""Require source-backed scope before recording a professor's intent approval."""

from pydantic_ai.exceptions import UnexpectedModelBehavior

from lecturepilot.learning_goal_scope_review import (
    read_approval_scope_review,
    review_learning_goal_scope,
    save_coherent_scope_review,
    scope_review_record,
)
from lecturepilot.model_client import ModelExecutionError
from lecturepilot.model_job_limits import bounded_model_job
from lecturepilot.models import ProviderCapability
from lecturepilot.practice_evidence_catalogue import evidence_catalogue


@bounded_model_job
async def require_approvable_scope(planner, *, root, intent, load_sources):
    settings = planner.provider_registry.require_ready(
        [ProviderCapability.CHAT, ProviderCapability.TOOL_CALLS, ProviderCapability.STRUCTURED_JSON]
    )
    review = read_approval_scope_review(root, intent_revision=intent.revision, settings=settings)
    if review is None:
        source, paths = await load_sources()
        catalogue = evidence_catalogue(source, paths)
        record = scope_review_record(
            root, intent_revision=intent.revision, catalogue=catalogue, settings=settings
        )
        try:
            async with planner._model(settings) as model:
                review = await review_learning_goal_scope(
                    model=model, settings=settings, proposal=intent, catalogue=catalogue
                )
        except UnexpectedModelBehavior as exc:
            raise ModelExecutionError("Learning goal scope could not be reviewed.") from exc
        save_coherent_scope_review(record, review)
    if not review.coherent:
        raise ValueError("Review the learning goals before approving: " + review.reason)
