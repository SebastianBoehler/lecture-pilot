from __future__ import annotations

import asyncio
from typing import Protocol

from lecturepilot.canvas_component_catalog import normalize_document_component_identities
from lecturepilot.canvas_models import CanvasDocument, CanvasSection
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_quality import CanvasQualityIssue
from lecturepilot.course_canvas_repair_preflight import normalize_repair_candidate
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


MAX_BATCHED_REPAIR_PASSES = 2


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
    active_candidate = normalize_document_component_identities(candidate)
    quality_batch = quality_issues is not None
    if quality_issues is None and failure_context.startswith("Canvas quality review failed:"):
        pending = await planner.review_quality(source, active_candidate)
        quality_batch = True
        if not pending:
            validate_planned_document(active_candidate, source)
            return active_candidate
    else:
        pending = quality_issues or [
            CanvasQualityIssue(section_id=section_id, block_id=block_id, reason=failure_context)
        ]
    for _ in range(MAX_BATCHED_REPAIR_PASSES):
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
        quality_batch = True
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
            _repair_issue_group(
                planner,
                source=source,
                candidate=candidate,
                issues=issues,
                quality_batch=quality_batch,
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


async def _repair_issue_group(
    planner: CanvasRepairPlanner,
    *,
    source: CanvasDocument,
    candidate: CanvasDocument,
    issues: list[CanvasQualityIssue],
    quality_batch: bool,
    output_language: str,
) -> CanvasDocument:
    active = candidate
    unresolved: list[CanvasQualityIssue] = []
    if quality_batch:
        for issue in issues:
            try:
                normalized = normalize_repair_candidate(
                    active,
                    issue.section_id,
                    issue.block_id,
                    issue.reason,
                    output_language=output_language,
                )
            except CanvasGenerationRepairableError:
                unresolved.append(issue)
                continue
            if normalized == active:
                unresolved.append(issue)
            active = normalized
    else:
        unresolved = issues
    if not unresolved:
        return active
    block_groups = _issues_by_block(unresolved)
    if len(block_groups) > 1 and all(group[0].block_id is not None for group in block_groups):
        for group in block_groups:
            active = await planner.repair_section(
                source,
                active,
                section_id=group[0].section_id,
                block_id=group[0].block_id,
                failure_context=_quality_failure_context(group),
                output_language=output_language,
            )
        return active
    return await planner.repair_section(
        source,
        active,
        section_id=unresolved[0].section_id,
        block_id=_shared_block_id(unresolved),
        failure_context=(
            _quality_failure_context(unresolved) if quality_batch else unresolved[0].reason
        ),
        output_language=output_language,
    )


def _shared_block_id(issues: list[CanvasQualityIssue]) -> str | None:
    block_ids = {issue.block_id for issue in issues}
    if len(block_ids) != 1:
        return None
    return next(iter(block_ids))


def _issues_by_block(issues: list[CanvasQualityIssue]) -> list[list[CanvasQualityIssue]]:
    grouped: dict[str | None, list[CanvasQualityIssue]] = {}
    for issue in issues:
        grouped.setdefault(issue.block_id, []).append(issue)
    return list(grouped.values())


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
