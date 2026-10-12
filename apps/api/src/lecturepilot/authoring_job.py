"""Bounded per-section canvas authoring.

Workflow, not agent: one call per missing section with deterministic section checks, one
lecture-level deterministic check, one critic pass and at most one targeted repair per flagged
section. Unresolved critic notes become draft warnings for professor review; only deterministic
invariants (and a source-checked conflict in an approved checkpoint) stop authoring.
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

from lecturepilot.authoring_checkpoint_review import CheckpointReviewer
from lecturepilot.authoring_limits import (
    AUTHORING_DEADLINE_SECONDS,
    AuthoringBudgetExceeded,
    authoring_budget,
)
from lecturepilot.authoring_instructions import defect_category, section_instructions
from lecturepilot.authoring_lock import exclusive_authoring_job
from lecturepilot.authoring_models import AuthoringDesignConflict, AuthoringMetrics, AuthoringResult
from lecturepilot.authoring_quality import AuthoringQualityMemo
from lecturepilot.authoring_state import load_state, save_state
from lecturepilot.authoring_workspace import AUTHORING_INPUT_ERRORS, AuthoringWorkspace
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_practice_support import source_for_practice_review
from lecturepilot.course_canvas_quality import CanvasQualityReviewer
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.metadata_events import emit_metadata_event
from lecturepilot.models import ProviderSettings
from lecturepilot.native_model_settings import native_model_settings
from lecturepilot.source_warnings import compact_source_warnings

SECTION_CONCURRENCY = 4


@dataclass
class AuthoringJob:
    root: Path
    source: CanvasDocument
    design: PracticeDesign
    source_revision: str
    settings: ProviderSettings
    reviewer: CanvasQualityReviewer
    checkpoint_reviewer: CheckpointReviewer = field(default_factory=CheckpointReviewer)
    output_language: str = "en"
    repair_context: str | None = None
    candidate: CanvasDocument | None = None
    escalate_design_conflicts: bool = True
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
        return AuthoringResult(workspace.document(), state.metrics)
    author = _SectionAuthor(job, workspace, model, state.metrics)
    missing = [
        p for p in workspace.paths if not workspace.fs.resolve(p, for_write=True).path.exists()
    ]
    await author.bounded(missing, author.write)
    await author.bounded(author.context_targets(), author.repair_context)
    await author.bounded(author.lecture_defects(), author.repair_defect)
    document = workspace.document()
    notes = await author.critic_notes(document)
    if notes:
        await author.bounded(list(notes), lambda path: author.repair(path, notes[path]))
        document = workspace.document()
        # One annotating pass: what remains is shown to the professor, never retried again.
        notes = await author.critic_notes(document, judge=False)
        document = document.model_copy(
            update={
                # Bounded like every canvas warning list: source OCR gaps collapse to one line
                # so open notes still fit beside a source already at the warning limit.
                "warnings": compact_source_warnings(
                    [
                        *(
                            f"Quality review left {len(items)} open note(s) in "
                            f"{workspace.paths[path].title!r}."
                            for path, items in notes.items()
                        ),
                        *document.warnings,
                    ]
                )
            }
        )
    state.metrics.elapsed_seconds += perf_counter() - started
    state.accepted_digest, state.completed = workspace.digest(), True
    job.authorize()
    save_state(job.root, state, [])
    job.report(state.metrics)
    return AuthoringResult(document, state.metrics)


class _SectionAuthor:
    def __init__(self, job, workspace, model, metrics):
        self.job, self.workspace, self.model, self.metrics = job, workspace, model, metrics
        self.memo = AuthoringQualityMemo()
        self.settings = native_model_settings(
            job.settings,
            temperature=0.4,
            reasoning_effort="low",
            prompt_cache_key=f"lp-canvas:{job.source_revision[:16]}:{job.design.revision[:16]}",
        )

    async def bounded(self, paths, run):
        limit = asyncio.Semaphore(SECTION_CONCURRENCY)

        async def one(path):
            async with limit:
                await run(path)

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

    async def critic_notes(self, document, *, judge=True) -> dict[str, list[str]]:
        self.job.authorize()
        self.metrics.quality_reviews += 1
        issues = await self.memo.review(
            self.job.reviewer,
            settings=self.job.settings,
            source_document=source_for_practice_review(self.job.source, document, self.job.design),
            candidate_document=document,
        )
        protected = {"practice-" + target.id for target in self.job.design.targets}

        async def resolve(issue):
            if not (judge and issue.block_id in protected):
                return issue
            try:
                # A confirmed design conflict raises and triggers one bounded teaching repair.
                return await self.job.checkpoint_reviewer.resolve(
                    job=self.job, document=document, issue=issue
                )
            except AuthoringDesignConflict as conflict:
                if self.job.escalate_design_conflicts:
                    raise
                return issue.model_copy(update={"reason": str(conflict)})

        resolved = await asyncio.gather(*(resolve(issue) for issue in issues))
        by_section = {section.id: section.source_section_id for section in document.sections}
        paths = {section.id: path for path, section in self.workspace.paths.items()}
        notes: dict[str, list[str]] = {}
        for issue in resolved:
            path = paths.get(by_section.get(issue.section_id, "")) if issue else None
            if path:
                notes.setdefault(path, []).append(issue.reason)
        return notes

    async def _author(self, path, task):
        self.job.authorize()
        section = self.workspace.paths[path]
        checkpoints = [target.id for target in self.workspace.targets[section.id]]
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
                f"for this section: {checkpoints}.\n{prediction}\n{task}"
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
