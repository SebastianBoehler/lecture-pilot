"""Bounded professor change request over an existing lecture canvas.

Workflow, not agent: at most one structured selection call (only when the professor names no
section), one change call per selected section with the ordinary per-section deterministic
checks, the lecture-level deterministic checks on the spliced lecture, ONE critic pass over the
changed sections only and at most one targeted repair per flagged section. Every other section
is the base document's own section. The request is untrusted instruction data: approved
checkpoints stay backend-inserted, so a change that needs another approved task fails with a
message that sends the professor to goal review. Critic objections to checkpoints stay
warnings; a change request never repairs the teaching implementation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field, replace
import re
import shutil

from pydantic_ai.exceptions import UsageLimitExceeded

from lecturepilot.authoring.authoring_critique import critique_document, critique_warnings
from lecturepilot.authoring.authoring_job import AuthoringJob, SectionAuthor
from lecturepilot.authoring.authoring_limits import (
    AUTHORING_DEADLINE_SECONDS,
    AuthoringBudgetExceeded,
    authoring_budget,
)
from lecturepilot.authoring.authoring_lock import exclusive_authoring_job
from lecturepilot.authoring.authoring_models import AuthoringMetrics
from lecturepilot.authoring.authoring_state import AuthoringStateError
from lecturepilot.authoring.authoring_workspace import AUTHORING_INPUT_ERRORS, AuthoringWorkspace
from lecturepilot.authoring.canvas_change_selection import select_change_sections
from lecturepilot.authoring.canvas_change_splice import splice_sections, validate_lecture
from lecturepilot.authoring.course_canvas_approved_checkpoints import RESERVED_CHECKPOINT_DEFECT
from lecturepilot.authoring.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.canvas.canvas_models import CanvasDocument

GOALS_CHANGE_MESSAGE = (
    "This change would alter an approved checkpoint. Approved learning goals and their tasks "
    "change only through goal review: edit the goals or use Regenerate goals, then draft again."
)
_DRAFT_PATH = re.compile(r"^/draft/[\w.-]+\.md:\s*")


class CanvasChangeRequestError(AuthoringStateError):
    """A change request that cannot be applied; the base draft or publication is unchanged."""


@dataclass(frozen=True)
class CanvasChangeResult:
    document: CanvasDocument
    metrics: AuthoringMetrics
    section_ids: tuple[str, ...]
    selection: str  # "professor" or "automatic"
    reasons: dict[str, str] = field(default_factory=dict)


async def run_change_job(
    job: AuthoringJob,
    *,
    model,
    base: CanvasDocument,
    instruction: str,
    section_ids: tuple[str, ...],
) -> CanvasChangeResult:
    job.authorize()
    # Critic objections to approved checkpoints stay warnings: no teaching repair here.
    job = replace(job, escalate_design_conflicts=False)
    with exclusive_authoring_job(job.root), authoring_budget():
        # A change request never resumes: replaying saved drafts would apply it twice.
        shutil.rmtree(job.root / "draft", ignore_errors=True)
        shutil.rmtree(job.root / "evidence", ignore_errors=True)
        (job.root / "initial-draft.json").unlink(missing_ok=True)
        try:
            async with asyncio.timeout(AUTHORING_DEADLINE_SECONDS):
                return await _run(job, model, base, instruction, section_ids)
        except UsageLimitExceeded as exc:
            raise AuthoringBudgetExceeded("Change request usage budget exhausted.") from exc
        except TimeoutError as exc:
            raise AuthoringBudgetExceeded("Change request deadline reached.") from exc


async def _run(job, model, base, instruction, section_ids) -> CanvasChangeResult:
    by_id = {section.id: section for section in base.sections}
    unknown = [section_id for section_id in section_ids if section_id not in by_id]
    if unknown:
        raise CanvasChangeRequestError(
            f"Section {unknown[0]!r} no longer exists in this lecture. Reload and try again."
        )
    try:
        workspace = AuthoringWorkspace(job.root, job.source, job.design, job.authorize, base)
    except ValueError as exc:
        raise CanvasChangeRequestError(
            "This lecture no longer matches its sources. Generate a new draft first."
        ) from exc
    metrics, reasons = AuthoringMetrics(), {}
    selection = "professor" if section_ids else "automatic"
    if not section_ids:
        reasons = await select_change_sections(
            settings=job.settings, model=model, base=base, instruction=instruction
        )
        metrics.model_requests += 1
        section_ids = tuple(reasons)
    paths = {section.id: path for path, section in workspace.paths.items()}
    targets = {}
    for section_id in section_ids:
        path = paths.get(by_id[section_id].source_section_id or "")
        if path is None:
            raise CanvasChangeRequestError(
                f"Section {by_id[section_id].title!r} cannot be changed on its own. "
                "Generate a new draft instead."
            )
        targets[path] = section_id
    author = SectionAuthor(job, workspace, model, metrics)
    request = f"Professor change request: {instruction}"
    await _sections(author.bounded(targets, lambda path: author.change(path, request)))
    document = await _checked(job, author, workspace, base, targets)
    changed = document.model_copy(
        update={"sections": [s for s in document.sections if s.id in targets.values()]}
    )
    critique = await critique_document(job, workspace, metrics, document=changed)
    pending = [path for path in critique.notes if path in targets]
    await _sections(author.bounded(pending, lambda path: author.repair(path, critique.notes[path])))
    if pending:
        document = await _checked(job, author, workspace, base, targets)
    document = document.model_copy(
        update={"warnings": critique_warnings(workspace, critique, document)}
    )
    job.report(metrics)
    return CanvasChangeResult(document, metrics, tuple(targets.values()), selection, reasons)


async def _checked(job, author, workspace, base, targets) -> CanvasDocument:
    """Splice and check the lecture; a named lecture-level defect gets one targeted repair."""
    for attempt in range(2):
        try:
            changed = {section_id: workspace.section(path) for path, section_id in targets.items()}
            document = splice_sections(base, changed, job.source)
            validate_lecture(document, job.source, job.design)
            return document
        except AUTHORING_INPUT_ERRORS as exc:
            message = str(exc)
            if RESERVED_CHECKPOINT_DEFECT in message:
                raise CanvasChangeRequestError(GOALS_CHANGE_MESSAGE) from exc
            named = [
                path
                for path, section_id in targets.items()
                if path in message or section_id in message
            ]
            if attempt or not named:
                raise CanvasChangeRequestError(_failure(message)) from exc
            await _sections(author.bounded(named, lambda path: author.repair(path, [message])))
    raise AssertionError("Unreachable change-request check state.")


async def _sections(work) -> None:
    """Section calls retry their deterministic checks; a remaining defect fails the request."""
    try:
        await work
    except CanvasGenerationRepairableError as exc:
        if RESERVED_CHECKPOINT_DEFECT in str(exc):
            raise CanvasChangeRequestError(GOALS_CHANGE_MESSAGE) from exc
        raise CanvasChangeRequestError(_failure(str(exc))) from exc


def _failure(message: str) -> str:
    detail = _DRAFT_PATH.sub("", message.strip())[:600]
    return f"The requested change could not be applied: {detail}"
