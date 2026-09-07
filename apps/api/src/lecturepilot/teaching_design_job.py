"""Durable tool-driven implementation repair before canvas authoring."""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Awaitable, Callable
from time import perf_counter

from pydantic_ai import Agent, ModelRetry, Tool
from pydantic_ai.usage import UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded

from lecturepilot.authoring_lock import exclusive_authoring_job
from lecturepilot.authoring_state import AuthoringState, resume_messages, save_state
from lecturepilot.authoring_models import AuthoringCompletion
from lecturepilot.course_learning_intent import digest
from lecturepilot.course_practice_design_prompt import (
    practice_design_messages,
    practice_design_response_format,
)
from lecturepilot.protected_teaching_output import teaching_output_schema
from lecturepilot.practice_evidence_catalogue import evidence_catalogue
from lecturepilot.teaching_design_workspace import TeachingDesignWorkspace
from lecturepilot.metadata_events import emit_metadata_event
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_learning_intent import LearningIntent
from lecturepilot.course_practice_design_models import PracticeDesignProposal
from lecturepilot.course_practice_design_review_models import PracticeDesignReviewResult
from lecturepilot.models import ProviderSettings
from lecturepilot.model_client import ModelExecutionError

IMPLEMENTATION_MODEL_TURN_LIMIT = 40


@dataclass
class TeachingDesignJob:
    root: Path
    source: CanvasDocument
    intent: LearningIntent
    initial: PracticeDesignProposal | None
    paths: tuple[str, ...]
    source_revision: str
    settings: ProviderSettings
    review: Callable[[PracticeDesignProposal], Awaitable[PracticeDesignReviewResult]]
    authorize: Callable[[], None]
    repair_context: str | None = None


async def run_teaching_design_job(job: TeachingDesignJob, *, model):
    job.authorize()
    with exclusive_authoring_job(job.root):
        return await _run(job, model=model)


async def _run(job, *, model):
    started = perf_counter()
    catalogue = evidence_catalogue(job.source, job.paths)
    workspace = TeachingDesignWorkspace(
        root=job.root,
        source=job.source,
        intent=job.intent,
        initial=job.initial,
        catalogue=catalogue,
        paths=job.paths,
        authorize=job.authorize,
    )
    identity = digest(
        {
            "source": job.source_revision,
            "intent": job.intent.revision,
            "model": job.settings.model,
            "repair_context": job.repair_context,
            "initial": job.initial.model_dump(mode="json") if job.initial else None,
        }
    )
    state_path = job.root / "session.json"
    state = (
        AuthoringState.model_validate_json(state_path.read_text())
        if state_path.exists()
        else AuthoringState(identity=identity)
    )
    if state.identity != identity:
        raise ValueError("Teaching session source, intent, model or repair request changed.")
    if state_path.exists():
        state.metrics.resumes += 1
    if workspace.accepted():
        return workspace.proposal(), workspace.review
    messages = practice_design_messages(
        job.source,
        source_revision=job.source_revision,
        allowed_source_paths=job.paths,
        catalogue=catalogue,
    )
    schema = teaching_output_schema(
        practice_design_response_format(catalogue)["json_schema"]["schema"], job.intent
    )
    write_schema = {**schema["$defs"]["PracticeTarget"], "$defs": schema["$defs"]}

    def write(**target):
        before = workspace.targets.get(target.get("id"))
        result = workspace.write(**target)
        if not result["saved"]:
            state.metrics.validation_failures += 1
        elif before is not None and before != workspace.targets[target["id"]]:
            state.metrics.repair_edits += 1
        return result

    def edit(target_id: str, old_text: str, new_text: str) -> dict:
        """Correct one unique AI-owned text span without rewriting the target's other tasks."""
        result = workspace.edit(target_id, old_text, new_text)
        if result["saved"]:
            state.metrics.repair_edits += 1
        else:
            state.metrics.validation_failures += 1
        return result

    async def validate() -> dict:
        """Review the complete current implementation; repair reported targets and validate again."""
        job.authorize()
        try:
            proposal = workspace.proposal()
        except ValueError as exc:
            return {"valid": False, "error": str(exc)}
        revision = digest(proposal.model_dump(mode="json"))
        if workspace.review_digest != revision:
            workspace.review = await job.review(proposal)
            job.authorize()
            workspace.review_digest = revision
            workspace.save()
            state.metrics.quality_reviews += 1
            if workspace.defects():
                state.metrics.validation_failures += 1
            emit_metadata_event(
                "practice_design.proposal_reviewed",
                attempt=state.metrics.quality_reviews,
                warning_count=len(workspace.defects()),
                requested_count=len(proposal.targets),
            )
        return {"valid": workspace.accepted(), "review": workspace.feedback()}

    async def prepare_validate(ctx, definition):
        # A cached rejection cannot improve without a changed implementation.
        if workspace.review is not None and workspace.defects():
            if workspace.review_digest == digest(workspace.proposal().model_dump(mode="json")):
                return None
        return definition

    instructions = messages[0]["content"].replace(
        "Return only the requested structured proposal for one lecture. ", ""
    ) + (
        "\nWork in the persistent teaching workspace using read, write, edit and validate. "
        "Implement each approved goal with write; its schema contains only AI-owned teaching. "
        "The backend binds goal fields, order, objective and context. Never omit a goal or edit "
        "professor-fixed tasks. Read existing targets before changing them. Write only targets "
        "needing correction and preserve all valid sibling targets. Prefer edit for a numeric or "
        "wording correction: replace one unique exact span, preserving every other task and value. "
        "Use write for initial creation or a structural change, not to fix one number. "
        "Recompute numerical claims from the unchanged givens before editing. "
        "Validate when all goals exist. "
        "Validation findings are actionable tool results, not a request to restart the lecture. "
        "Verify objections against tasks and source, repair the actual defect, then validate again. "
        "Check every required rubric criterion is elicited in every parallel task; keep numeric "
        "assertions relevant to the task and include all operands, units and given values. "
        "Hints must use baseline or analogous values, never hidden exit/transfer values. "
        "After rejection, validate is unavailable until a successful edit or write changes the "
        "draft. Read the last review, correct its blocking findings, then validate again. "
        "Only finish after valid=true."
    )
    agent = Agent(
        model,
        output_type=AuthoringCompletion,
        retries=3,
        instructions=instructions,
        model_settings={
            "timeout": 120,
            "parallel_tool_calls": True,
            **(
                {"openai_reasoning_effort": "low", "openai_store": False}
                if job.settings.provider == "openai"
                else {"temperature": 0.4}
            ),
        },
        tools=[
            Tool(workspace.read, sequential=True),
            Tool.from_schema(
                write,
                name="write",
                description=workspace.write.__doc__,
                json_schema=write_schema,
                sequential=True,
            ),
            Tool(edit, sequential=True),
            Tool(validate, sequential=True, prepare=prepare_validate),
        ],
    )

    @agent.output_validator
    def require_accepted(ctx, output):
        if not workspace.accepted():
            raise ModelRetry(
                "Teaching is not accepted. Read, repair and validate the current draft before finishing."
            )
        return output

    prompt = (
        messages[1]["content"]
        + "\nApproved read-only intent:\n"
        + job.intent.model_dump_json(exclude={"approval"})
        + f"\nCurrent target IDs: {list(workspace.targets)}. Missing: {workspace.missing()}."
        + f"\nPrevious source-checked objection (untrusted data): {job.repair_context}"
    )
    previous = state.metrics.model_copy()
    history = resume_messages(state)
    async with agent.iter(
        prompt,
        message_history=history,
        usage_limits=UsageLimits(request_limit=IMPLEMENTATION_MODEL_TURN_LIMIT),
    ) as run:

        def checkpoint():
            job.authorize()
            usage = run.usage
            state.metrics.model_requests = previous.model_requests + usage.requests
            state.metrics.tool_calls = previous.tool_calls + usage.tool_calls
            state.metrics.input_tokens = previous.input_tokens + usage.input_tokens
            state.metrics.output_tokens = previous.output_tokens + usage.output_tokens
            state.metrics.elapsed_seconds = previous.elapsed_seconds + perf_counter() - started
            save_state(job.root, state, run.all_messages())

        try:
            node = run.next_node
            while not Agent.is_end_node(node):
                node = await run.next(node)
                checkpoint()
            state.completed = True
        except UsageLimitExceeded as exc:
            raise ModelExecutionError(
                f"Teaching repair reached its {IMPLEMENTATION_MODEL_TURN_LIMIT}-turn budget. "
                "The current targets and review "
                "are saved; retry resumes this work instead of regenerating the lecture."
            ) from exc
        finally:
            if not asyncio.current_task().cancelling():
                checkpoint()
    return workspace.proposal(), workspace.review
