from __future__ import annotations

import asyncio
from typing import Protocol

from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_quality import CanvasQualityIssue
from lecturepilot.course_canvas_validation import validate_planned_document


class CanvasRepairPlanner(Protocol):
    async def repair_section(
        self,
        source_document: CanvasDocument,
        candidate_document: CanvasDocument,
        *,
        section_id: str,
        block_id: str | None,
        failure_context: str,
        output_language: str,
    ) -> CanvasDocument: ...

    async def review_quality(
        self,
        source_document: CanvasDocument,
        candidate_document: CanvasDocument,
    ) -> list[CanvasQualityIssue]: ...


async def repair_until_quality_valid(
    planner: CanvasRepairPlanner,
    *,
    source: CanvasDocument,
    candidate: CanvasDocument,
    section_id: str,
    block_id: str | None,
    failure_context: str,
    output_language: str,
    quality_issues: list[CanvasQualityIssue] | None = None,
) -> CanvasDocument:
    active_candidate = candidate
    pending = quality_issues or [
        CanvasQualityIssue(section_id=section_id, block_id=block_id, reason=failure_context)
    ]
    quality_batch = quality_issues is not None
    try:
        active_candidate = await _repair_sections_once(
            planner,
            source=source,
            candidate=active_candidate,
            issue_groups=_issues_by_section(pending),
            quality_batch=quality_batch,
            output_language=output_language,
        )
        validate_planned_document(active_candidate, source)
    except CanvasGenerationRepairableError as exc:
        raise exc.with_candidate(exc.candidate or active_candidate)
    pending = await planner.review_quality(source, active_candidate)
    if not pending:
        return active_candidate
    first = pending[0]
    raise CanvasGenerationRepairableError(
        _quality_failure_context(pending),
        candidate=active_candidate,
        section_id=first.section_id,
        block_id=first.block_id if len(pending) == 1 else None,
    )


async def _repair_sections_once(
    planner: CanvasRepairPlanner,
    *,
    source: CanvasDocument,
    candidate: CanvasDocument,
    issue_groups: list[list[CanvasQualityIssue]],
    quality_batch: bool,
    output_language: str,
) -> CanvasDocument:
    tasks = [
        asyncio.create_task(
            planner.repair_section(
                source,
                candidate,
                section_id=issues[0].section_id,
                block_id=issues[0].block_id if len(issues) == 1 else None,
                failure_context=(
                    _quality_failure_context(issues) if quality_batch else issues[0].reason
                ),
                output_language=output_language,
            )
        )
        for issues in issue_groups
    ]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
    failure = next((task.exception() for task in done if task.exception() is not None), None)
    if failure is not None:
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        raise failure
    results = [task.result() for task in tasks]
    replacements = {
        issues[0].section_id: _section(result, issues[0].section_id)
        for issues, result in zip(issue_groups, results, strict=True)
    }
    return candidate.model_copy(
        update={
            "sections": [replacements.get(section.id, section) for section in candidate.sections]
        }
    )


def _section(document: CanvasDocument, section_id: str) -> CanvasSection:
    return next(section for section in document.sections if section.id == section_id)


def _issues_by_section(
    issues: list[CanvasQualityIssue],
) -> list[list[CanvasQualityIssue]]:
    grouped: dict[str, list[CanvasQualityIssue]] = {}
    for issue in issues:
        grouped.setdefault(issue.section_id, []).append(issue)
    return list(grouped.values())


def _quality_failure_context(issues: list[CanvasQualityIssue]) -> str:
    details = "\n".join(f"- {issue.reason}" for issue in issues)
    return f"Canvas quality review failed: fix every reported issue together:\n{details}"
