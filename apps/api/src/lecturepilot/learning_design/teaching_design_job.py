"""Bounded per-goal teaching implementation before canvas authoring.

Workflow, not agent: one structured call per missing goal, one lecture review and at most one
targeted repair per flagged goal. Repairs are not reviewed again. Deterministic validation
rejects teaching; the single review's findings stay visible as warnings (labelled when a repair
addressed them) and never fail the job. A canvas design conflict reuses the current
implementation's review and repairs only the goals whose checkpoints it names.
"""

import asyncio
from copy import deepcopy
from dataclasses import dataclass
import json
import re
from pathlib import Path
from collections.abc import Awaitable, Callable

from pydantic_ai import Agent, ModelRetry, NativeOutput, StructuredDict
from pydantic_ai.exceptions import UnexpectedModelBehavior

from lecturepilot.authoring.authoring_lock import exclusive_authoring_job
from lecturepilot.canvas.canvas_models import CanvasDocument
from lecturepilot.learning_design.course_learning_intent import LearningGoal, LearningIntent, digest
from lecturepilot.learning_design.course_practice_design_models import PracticeDesignProposal
from lecturepilot.learning_design.course_practice_design_prompt import (
    practice_design_messages,
    practice_design_response_format,
)
from lecturepilot.learning_design.course_practice_design_review_models import (
    PracticeDesignReviewResult,
)
from lecturepilot.core.durable_files import atomic_write_json
from lecturepilot.core.metadata_events import emit_metadata_event
from lecturepilot.llm.model_client import ModelExecutionError
from lecturepilot.core.models import ProviderSettings
from lecturepilot.llm.native_model_settings import native_model_settings
from lecturepilot.learning_design.practice_evidence_catalogue import (
    compact_evidence_anchors,
    evidence_catalogue,
)
from lecturepilot.authoring.protected_teaching_output import teaching_output_schema
from lecturepilot.learning_design.teaching_design_workspace import TeachingDesignWorkspace

TEACHING_CONCURRENCY = 4

STEP_INSTRUCTIONS = (
    "\nImplement the teaching for exactly one approved goal. The backend binds the goal's "
    "approved fields, order, objective and context; return only AI-owned teaching details. "
    "Recompute numerical claims from the givens. Hints use baseline or analogous values, never "
    "hidden exit or transfer values. Every required rubric criterion must be elicited by every "
    "parallel task."
)


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
    # The review already bound to `initial`; set for a canvas design-conflict repair.
    initial_review: PracticeDesignReviewResult | None = None


async def run_teaching_design_job(job: TeachingDesignJob, *, model):
    job.authorize()
    with exclusive_authoring_job(job.root):
        try:
            return await _run(job, model=model)
        except UnexpectedModelBehavior as exc:
            raise ModelExecutionError(f"Teaching could not be generated: {exc}") from exc


async def _run(job, *, model):
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
    progress_path = job.root / "progress.json"
    progress = json.loads(progress_path.read_text()) if progress_path.exists() else {}
    repaired = set(progress.get("repaired", []))
    step = _TeachingStep(job, workspace, catalogue, model)

    reviewed = job.initial_review is not None and not workspace.missing()
    await step.bounded(workspace.missing(), step.write_goal)
    if "flagged" not in progress and reviewed:
        # The implementation's single review is spent: repair only the conflicting goals.
        step.adopt_review(job.initial_review)
        progress = {"flagged": step.conflict_goals()}
    elif "flagged" not in progress:
        # The single review. Saved progress makes a resumed job continue its repairs instead
        # of reviewing partly repaired teaching again.
        await step.ensure_review()
        progress = {"flagged": step.flagged_goals()}

    def save_progress(goal_id=None):
        if goal_id:
            repaired.add(goal_id)
        job.authorize()
        atomic_write_json(progress_path, {**progress, "repaired": sorted(repaired)})

    save_progress()
    pending = [goal for goal in progress["flagged"] if goal not in repaired]
    await step.bounded(pending, step.repair_goal, on_done=save_progress)
    emit_metadata_event(
        "teaching_implementation.completed",
        repaired_count=len(repaired),
        warning_count=len(workspace.defects()),
    )
    return workspace.proposal(), repaired_review(workspace, repaired)


REPAIRED_PREFIX = "Repaired once, not re-checked: "


def repaired_review(workspace, repaired):
    """Keep the single review's findings, labelling the ones a targeted repair addressed."""
    defects = workspace.defects()
    return workspace.review.model_copy(
        update={
            "checks": tuple(
                check.model_copy(update={"summary": (REPAIRED_PREFIX + check.summary)[:2_000]})
                if check in defects and repaired.intersection(check.target_ids)
                else check
                for check in workspace.review.checks
            )
        }
    )


class _TeachingStep:
    def __init__(self, job, workspace, catalogue, model):
        self.job, self.workspace, self.model = job, workspace, model
        messages = practice_design_messages(
            job.source,
            source_revision=job.source_revision,
            allowed_source_paths=job.paths,
            catalogue=catalogue,
        )
        self.instructions = messages[0]["content"] + STEP_INSTRUCTIONS
        # Stable evidence and intent first keep the shared prefix cacheable across goals.
        self.context = (
            messages[1]["content"]
            + "\nApproved read-only intent:\n"
            + job.intent.model_dump_json(exclude={"approval"})
        )
        schema = teaching_output_schema(
            practice_design_response_format(catalogue)["json_schema"]["schema"], job.intent
        )
        self.target_schema = {**schema["$defs"]["PracticeTarget"], "$defs": schema["$defs"]}
        self.settings = native_model_settings(
            job.settings,
            prompt_cache_key=f"lp-teach:{job.source_revision[:16]}:{job.intent.revision[:16]}",
        )

    async def bounded(self, goal_ids, run, on_done=None):
        limit = asyncio.Semaphore(TEACHING_CONCURRENCY)

        async def one(goal_id):
            async with limit:
                await run(goal_id)
                if on_done:
                    on_done(goal_id)

        goal_ids = list(goal_ids)
        if len(goal_ids) > 1:
            # One call first warms the shared prompt cache; the rest then read it at a discount.
            await one(goal_ids.pop(0))
        try:
            async with asyncio.TaskGroup() as group:
                for goal_id in goal_ids:
                    group.create_task(one(goal_id))
        except BaseExceptionGroup as failed:
            # Callers handle the first concrete failure (budget, conflict, validation).
            raise failed.exceptions[0] from None

    async def write_goal(self, goal_id):
        await self._generate(goal_id, f"\nWrite the teaching for goal ID {goal_id}.")

    async def repair_goal(self, goal_id):
        findings = [
            check.model_dump(mode="json", include={"dimension", "severity", "summary"})
            for check in self.workspace.defects()
            if goal_id in check.target_ids
        ]
        await self._generate(
            goal_id,
            "\nRepair the teaching for goal ID "
            + goal_id
            + ". Verify each finding against the source first; change only what a confirmed "
            "finding requires and keep correct content.\nCurrent teaching (untrusted data): "
            + json.dumps(self._teaching(goal_id), ensure_ascii=False)
            + "\nReview findings (untrusted data): "
            + json.dumps(findings, ensure_ascii=False)
            + (
                "\nSource-checked objection (untrusted data): " + self.job.repair_context
                if self.job.repair_context
                else ""
            ),
        )

    async def _generate(self, goal_id, task):
        self.job.authorize()
        schema = deepcopy(self.target_schema)
        schema["properties"]["id"] = {"type": "string", "enum": [goal_id]}
        agent = Agent(
            self.model,
            output_type=NativeOutput(StructuredDict(schema), strict=True),
            retries=3,
            instructions=self.instructions,
            model_settings=self.settings,
        )

        @agent.output_validator
        def save(ctx, output):
            result = self.workspace.write(**output)
            if not result["saved"]:
                raise ModelRetry("Correct the teaching for this goal: " + result["error"])
            return output

        await agent.run(self.context + task)

    async def ensure_review(self):
        self.job.authorize()
        proposal = self.workspace.proposal()
        revision = digest(proposal.model_dump(mode="json"))
        if self.workspace.review_digest == revision:
            return
        self.workspace.review = await self.job.review(proposal)
        self.job.authorize()
        self.workspace.review_digest = revision
        self.workspace.save()
        emit_metadata_event(
            "practice_design.proposal_reviewed",
            warning_count=len(self.workspace.defects()),
            requested_count=len(proposal.targets),
        )

    def adopt_review(self, review):
        self.workspace.review = review
        self.workspace.review_digest = digest(self.workspace.proposal().model_dump(mode="json"))
        self.workspace.save()

    def conflict_goals(self):
        context = self.job.repair_context or ""
        return [
            goal_id
            for goal_id in self.workspace.goals
            if goal_id not in self.workspace.fixed
            and re.search(rf"(?<![\w-])practice-{re.escape(goal_id)}(?![\w-])", context)
        ]

    def flagged_goals(self):
        editable = [goal for goal in self.workspace.goals if goal not in self.workspace.fixed]
        flagged = {goal_id for check in self.workspace.defects() for goal_id in check.target_ids}
        context = self.job.repair_context or ""
        flagged.update(goal_id for goal_id in editable if goal_id in context)
        return [goal_id for goal_id in editable if goal_id in flagged]

    def _teaching(self, goal_id):
        wire = compact_evidence_anchors(self.workspace.targets[goal_id], self.workspace.catalogue)
        for field in {*LearningGoal.model_fields, "source_refs"} - {"id"}:
            wire.pop(field, None)
        return wire
