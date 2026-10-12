"""The single annotating critic pass of canvas authoring.

The critic reviews the whole lecture once and classifies objections to approved checkpoints
itself (dismiss, repair_section or design_conflict, with verified evidence IDs). Ordinary notes
get one targeted section repair and are never re-reviewed; what they flagged stays visible as a
draft warning. A verified design_conflict triggers one bounded teaching repair; once that is
spent, further conflicts become warnings and never section edits of approved tasks.
"""

from lecturepilot.authoring.authoring_models import AuthoringDesignConflict
from lecturepilot.authoring.authoring_state import AuthoringCritique
from lecturepilot.core.metadata_events import emit_metadata_event
from lecturepilot.sources.source_warnings import compact_source_warnings


async def critique_document(job, workspace, metrics) -> AuthoringCritique:
    job.authorize()
    document = workspace.document()
    metrics.quality_reviews += 1
    issues = await job.reviewer.review(
        settings=job.settings,
        source_document=job.source,
        candidate_document=document,
        design=job.design,
    )
    job.authorize()
    by_section = {section.id: section.source_section_id for section in document.sections}
    paths = {section.id: path for path, section in workspace.paths.items()}
    critique, conflicts = AuthoringCritique(), []
    for issue in issues:
        if issue.decision != "repair_section" or (issue.block_id or "").startswith("practice-"):
            emit_metadata_event(
                "checkpoint.objection_resolved",
                outcome=issue.decision,
                section_id=issue.section_id,
                source_count=len(issue.evidence_ids),
            )
        path = paths.get(by_section.get(issue.section_id, ""))
        if issue.decision == "dismiss" or path is None:
            continue
        if issue.decision == "design_conflict":
            if job.escalate_design_conflicts:
                conflicts.append(f"{issue.block_id}: {issue.reason}")
            else:
                critique.disputed.setdefault(path, []).append(issue.reason)
            continue
        critique.notes.setdefault(path, []).append(issue.reason)
    if conflicts:
        # Names the checkpoint (and so its goal ID) for the one targeted teaching repair.
        raise AuthoringDesignConflict(
            "A source-checked objection requires revising the approved practice design: "
            + "; ".join(conflicts)
        )
    return critique


def critique_warnings(workspace, critique: AuthoringCritique, document) -> list[str]:
    def title(path):
        return workspace.paths[path].title

    return compact_source_warnings(
        [
            *(
                f"Quality review flagged {len(items)} note(s) in {title(path)!r}; "
                "repaired once, not re-checked."
                for path, items in critique.notes.items()
            ),
            *(
                f"Quality review left {len(items)} open note(s) on approved checkpoints in "
                f"{title(path)!r}."
                for path, items in critique.disputed.items()
            ),
            # Bounded like every canvas warning list: source OCR gaps collapse to one line
            # so review notes still fit beside a source already at the warning limit.
            *document.warnings,
        ]
    )
