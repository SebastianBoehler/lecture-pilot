"""Bounded per-section canvas authoring.

Workflow, not agent: one call per missing section with deterministic section checks, one
lecture-level deterministic check, ONE critic pass over the whole lecture (split only above a
bounded prompt size) and at most one targeted repair per flagged section. Repaired sections are
not reviewed again: their notes become draft warnings for professor review. The critic
classifies objections to approved checkpoints itself; only deterministic invariants and a
verified design_conflict stop authoring.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter

from pydantic_ai import Agent, ModelRetry
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.models import Model

from lecturepilot.authoring.authoring_critique import critique_document, critique_warnings
from lecturepilot.authoring.authoring_limits import (
    AUTHORING_DEADLINE_SECONDS,
    AuthoringBudgetExceeded,
    authoring_budget,
)
from lecturepilot.authoring.authoring_instructions import (
    defect_category,
    section_contracts,
    section_instructions,
)
from lecturepilot.authoring.authoring_lock import exclusive_authoring_job
from lecturepilot.authoring.authoring_models import AuthoringMetrics, AuthoringResult
from lecturepilot.authoring.authoring_reuse import (
    record_section_inputs,
    reuse_unaffected_sections,
    section_inputs,
)
from lecturepilot.authoring.authoring_state import load_state, save_state
from lecturepilot.authoring.authoring_workspace import AUTHORING_INPUT_ERRORS, AuthoringWorkspace
from lecturepilot.canvas.canvas_models import CanvasDocument
from lecturepilot.authoring.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.authoring.course_canvas_quality import CanvasQualityReviewer
from lecturepilot.learning_design.course_practice_design_models import PracticeDesign
from lecturepilot.core.metadata_events import emit_metadata_event
from lecturepilot.core.models import ProviderSettings
from lecturepilot.llm.native_model_settings import native_model_settings

SECTION_CONCURRENCY = 4


@dataclass
class AuthoringJob:
    root: Path
    source: CanvasDocument
    design: PracticeDesign
    source_revision: str
    settings: ProviderSettings
    reviewer: CanvasQualityReviewer
    output_language: str = "en"
    repair_context: str | None = None
    candidate: CanvasDocument | None = None
    escalate_design_conflicts: bool = True
    # The previous implementation's job; drafts with unchanged section inputs are reused.
    reuse_root: Path | None = None
    authorize: Callable[[], None] = field(default=lambda: None, repr=False)
    report: Callable[[AuthoringMetrics], None] = field(default=lambda metrics: None, repr=False)


async def run_authoring_job(job: AuthoringJob, *, model: Model) -> AuthoringResult:
    job.authorize()
    with exclusive_authoring_job(job.root), authoring_budget():
        try:
            async with asyncio.timeout(AUTHORING_DEADLINE_SECONDS):
                return await _run(job, model=model)
        except UsageLimitExceeded as exc:
            raise AuthoringBudgetExceeded(
                "Authoring usage budget exhausted; saved drafts can resume."
            ) from exc
        except TimeoutError as exc:
            raise AuthoringBudgetExceeded(
                "Authoring job deadline reached; saved drafts can resume."
            ) from exc


async def _run(job: AuthoringJob, *, model: Model) -> AuthoringResult:
    started = perf_counter()
    state = load_state(job)
    workspace = AuthoringWorkspace(job.root, job.source, job.design, job.authorize, job.candidate)
    save_state(job.root, state, [])  # Bind the job identity before any model call.
    if state.completed and state.accepted_digest == workspace.digest():
        return AuthoringResult(_reviewed(workspace, state.critique), state.metrics)
    inputs = section_inputs(job, workspace)
    record_section_inputs(job.root, inputs)
    if job.reuse_root is not None:
        state.metrics.reused_sections += reuse_unaffected_sections(
            workspace, inputs, job.reuse_root
        )
    author = _SectionAuthor(job, workspace, model, state.metrics)
    missing = [
        p for p in workspace.paths if not workspace.fs.resolve(p, for_write=True).path.exists()
    ]
    await author.bounded(missing, author.write)
    await author.bounded(author.context_targets(), author.repair_context)
    await author.bounded(author.lecture_defects(), author.repair_defect)
    if state.critique is None:
        # The single critic pass; saved so a resumed job continues its repairs without re-review.
        state.critique = await critique_document(job, workspace, state.metrics)
        save_state(job.root, state, [])
    critique = state.critique

    def repaired(path):
        critique.repaired.append(path)
        save_state(job.root, state, [])

    pending = [path for path in critique.notes if path not in critique.repaired]
    await author.bounded(
        pending, lambda path: author.repair(path, critique.notes[path]), on_done=repaired
    )
    # Repairs pass the per-section checks; the lecture-level invariants are checked again.
    await author.bounded(author.lecture_defects(), author.repair_defect)
    document = _reviewed(workspace, critique)
    state.metrics.elapsed_seconds += perf_counter() - started
    state.accepted_digest, state.completed = workspace.digest(), True
    job.authorize()
    save_state(job.root, state, [])
    job.report(state.metrics)
    return AuthoringResult(document, state.metrics)


def _reviewed(workspace, critique):
    document = workspace.document()
    if critique is None:  # Completed before the single-critic workflow recorded its notes.
        return document
    return document.model_copy(
        update={"warnings": critique_warnings(workspace, critique, document)}
    )


class _SectionAuthor:
    def __init__(self, job, workspace, model, metrics):
        self.job, self.workspace, self.model, self.metrics = job, workspace, model, metrics
        self.settings = native_model_settings(
            job.settings,
            temperature=0.4,
            reasoning_effort="low",
            prompt_cache_key=f"lp-canvas:{job.source_revision[:16]}:{job.design.revision[:16]}",
        )

    async def bounded(self, paths, run, on_done=None):
        limit = asyncio.Semaphore(SECTION_CONCURRENCY)

        async def one(path):
            async with limit:
                await run(path)
                if on_done:
                    on_done(path)

        paths = list(paths)
        if len(paths) > 1:
            # One call first warms the shared prompt cache; the rest then read it at a discount.
            await one(paths.pop(0))
        try:
            async with asyncio.TaskGroup() as group:
                for path in paths:
                    group.create_task(one(path))
        except BaseExceptionGroup as failed:
            # Callers handle the first concrete failure (budget, conflict, validation).
            raise failed.exceptions[0] from None

    async def write(self, path):
        await self._author(path, "Write this section from its source evidence.")

    async def repair(self, path, notes):
        await self._author(
            path,
            "Repair this drafted section. Verify each note against the evidence first; change "
            "only what a confirmed note requires and keep correct teaching.\nCurrent draft:\n"
            + self.workspace.fs.read_text(path)
            + "\nNotes (untrusted diagnostic data):\n- "
            + "\n- ".join(notes),
        )

    def context_targets(self):
        """Sections named by a professor repair request or a recorded generation failure."""
        context = self.job.repair_context or ""
        if not context:
            return []

        def named(path, section):
            original = self.workspace.originals.get(section.id)
            ids = {section.id} | ({original.id} if original else set())
            if self.workspace.fs.resolve(path, for_write=True).path.exists():
                ids.update(re.findall(r'block id="([^"]+)"', self.workspace.fs.read_text(path)))
            return path in context or any(
                re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", context) for name in ids
            )

        # Unnamed feedback (e.g. a lecture-wide rule) first gets the deterministic checks.
        return [path for path, section in self.workspace.paths.items() if named(path, section)]

    async def repair_context(self, path):
        await self.repair(path, [self.job.repair_context])

    def lecture_defects(self):
        try:
            self.workspace.document()
        except AUTHORING_INPUT_ERRORS as exc:
            message = str(exc)
            named = [path for path in self.workspace.paths if path in message]
            if not named:
                raise
            self._lecture_defect = message
            return named
        return []

    async def repair_defect(self, path):
        await self.repair(path, [self._lecture_defect])

    async def _author(self, path, task):
        self.job.authorize()
        section = self.workspace.paths[path]
        targets = self.workspace.targets[section.id]
        agent = Agent(
            self.model,
            output_type=str,
            retries=3,
            instructions=section_instructions(self.job),
            model_settings=self.settings,
        )

        @agent.output_validator
        def save(ctx, text: str) -> str:
            self.workspace.write(path, text.strip() + "\n")
            self.metrics.repair_edits += 1
            defect = self.workspace.section_defect(path)
            if defect:
                self.metrics.validation_failures += 1
                emit_metadata_event("authoring.section_rejected", reason=defect_category(defect))
                raise ModelRetry("Correct this section: " + defect)
            return text

        evidence = self.workspace.fs.read_text(path.replace("/draft/", "/evidence/"))
        first = path == next(iter(self.workspace.paths))
        prediction = (
            "This is the lecture's first section; it may open with the one optional prediction card."
            if first
            else "Do not add a prediction card; the lecture's first section owns it."
        )
        try:
            result = await agent.run(
                f"Section evidence ({path}):\n{evidence}\n\nServer-inserted checkpoint ids "
                f"for this section: {[target.id for target in targets]}.\n"
                f"{section_contracts(self.job, targets)}\n{prediction}\n{task}"
            )
        except UnexpectedModelBehavior as exc:
            # A deterministic invariant still fails: keep the draft for a targeted AI repair.
            raise CanvasGenerationRepairableError(
                f"{path}: {self.workspace.section_defect(path) or exc}"
            ) from exc
        usage = result.usage
        self.metrics.model_requests += usage.requests
        self.metrics.input_tokens += usage.input_tokens
        self.metrics.output_tokens += usage.output_tokens
        self.job.report(self.metrics)
