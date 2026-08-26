from types import SimpleNamespace
import json

from lecturepilot.course_practice_design_models import (
    PracticeDesign,
    PracticeDesignProposal,
    PracticeEvidenceCriterion,
    PracticeHint,
    PracticeMisconception,
    PracticeTarget,
)
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument
from lecturepilot.course_canvas_evidence_batches import group_evidence_sections
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.course_canvas_validation import source_topic_sections
from lecturepilot.course_practice_design_store import PracticeDesignStore
from practice_design_review_test_helpers import passing_review, source_document
from lecturepilot.storage_layout import StorageLayout


def proposal() -> PracticeDesignProposal:
    source_anchor = {"source_path": "lecture-01.md", "excerpt": "evidence"}
    return PracticeDesignProposal(
        lecture_title="Practice design",
        objective="Derive the conclusion independently from the cited evidence.",
        planning_context={
            "learner_level": "Undergraduate learners in this lecture.",
            "prerequisites": ["Interpret the supplied evidence."],
            "time_budget_minutes": 30,
            "allowed_aids": ["Course notes"],
            "assessment_conditions": "Complete each assessment individually.",
            "insufficiencies": [],
        },
        targets=[
            PracticeTarget(
                id="derive-conclusion",
                title="Derive a conclusion",
                outcome="Derive a justified conclusion from the given evidence.",
                outcome_anchor=source_anchor,
                target_invariant="Connect the relevant evidence to a justified conclusion.",
                target_invariant_anchor=source_anchor,
                baseline_task="Derive the conclusion from the stated evidence and justify the reasoning.",
                baseline_task_anchor=source_anchor,
                independent_exit_task="Derive a conclusion from a parallel evidence set and justify it.",
                independent_exit_task_anchor=source_anchor,
                independent_exit_surface_change="Change the evidence details, not the reasoning.",
                delayed_transfer_task="Derive a conclusion after the surface details change and justify it.",
                delayed_transfer_task_anchor=source_anchor,
                delayed_transfer_surface_change=(
                    "Change the scenario and representation without adding new knowledge."
                ),
                evidence_criteria=[
                    PracticeEvidenceCriterion(
                        id="cite-evidence",
                        description="Cites the relevant evidence.",
                        source_anchor=source_anchor,
                    )
                ],
                misconceptions=[
                    PracticeMisconception(
                        id="ignore-evidence",
                        description="States a conclusion without evidence.",
                        diagnostic_cue="The response omits a source-grounded reason.",
                        source_anchor=source_anchor,
                    )
                ],
                hint_ladder=[
                    PracticeHint(
                        level="prompt",
                        content="Identify the key evidence.",
                        source_anchor=source_anchor,
                    )
                ],
                review_after_days=7,
                source_refs=["lecture-01.md"],
            )
        ],
    )


def target(**changes: object) -> PracticeTarget:
    changes = dict(changes)
    source_excerpt = str(changes.pop("source_excerpt", "evidence"))
    payload = {**proposal().targets[0].model_dump(mode="json"), **changes}
    source_refs = tuple(payload["source_refs"])
    source_path = source_refs[0]
    anchor = {"source_path": source_path, "excerpt": source_excerpt}
    for field in (
        "outcome_anchor",
        "target_invariant_anchor",
        "baseline_task_anchor",
        "independent_exit_task_anchor",
        "delayed_transfer_task_anchor",
    ):
        if "source_refs" in changes and field not in changes:
            payload[field] = anchor
    for field in ("evidence_criteria", "misconceptions", "hint_ladder"):
        payload[field] = [
            {
                **item,
                "source_anchor": (
                    anchor if "source_refs" in changes else item.get("source_anchor") or anchor
                ),
            }
            for item in payload[field]
        ]
    return PracticeTarget(**payload)


def document(task: str) -> SimpleNamespace:
    block = SimpleNamespace(id="practice-derive-conclusion", type="checkpoint", text=task)
    section = SimpleNamespace(source_ref="lecture-01.md", blocks=[block])
    return SimpleNamespace(sections=[section])


def canvas_with_practice_design(
    document: CanvasDocument, practice_design: PracticeDesign | None = None
) -> tuple[CanvasDocument, PracticeDesign]:
    design = practice_design or practice_design_for_canvas(document)
    target = design.targets[0]
    first = document.sections[0]
    if practice_design is not None:
        first = first.model_copy(update={"source_ref": target.source_refs[0]})
    checkpoint = CanvasBlock(
        id=f"practice-{target.id}", type="checkpoint", text=target.baseline_task
    )
    first = first.model_copy(update={"blocks": [*first.blocks, checkpoint]})
    return document.model_copy(update={"sections": [first, *document.sections[1:]]}), design


def practice_design_for_canvas(document: CanvasDocument) -> PracticeDesign:
    source_section = group_evidence_sections(
        source_topic_sections(document) or document.sections,
        document_source_ref=document.source_ref,
    )[0]
    source_excerpt = next(
        (
            value
            for block in source_section.blocks
            for value in (block.text, block.caption, *block.items)
            if value
        ),
        source_section.title,
    )[:1_600]
    design_target = target(
        baseline_task="Derive the conclusion from the stated evidence and justify the reasoning.",
        independent_exit_task="Derive a conclusion from a parallel evidence set and justify it.",
        delayed_transfer_task="Derive a conclusion after the surface details change and justify it.",
        source_refs=(source_section.source_ref or document.source_ref,),
        source_excerpt=source_excerpt,
    )
    draft = proposal()
    return PracticeDesign.create(
        course_id=document.course_id,
        lecture_id=document.lecture_id,
        lecture_title=document.title,
        objective="Derive the conclusion independently from the cited evidence.",
        planning_context=draft.planning_context,
        source_revision="a" * 64,
        targets=(design_target,),
    )


def write_manifest(
    layout: StorageLayout, *, course_id: str, lecture_id: str, source_path: str
) -> None:
    index = json.loads(layout.course_source_index_path(course_id).read_text())
    source = next(item for item in index["files"] if item["path"] == source_path)
    path = layout.lecture_source_manifest_path(course_id, lecture_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "course_id": course_id,
                "lecture_id": lecture_id,
                "files": [{"path": source_path, "sha256": source["sha256"]}],
            }
        )
    )


def save_approved_design(
    layout: StorageLayout, *, course_id: str, lecture_id: str, source_path: str
) -> None:
    revision = lecture_source_revision(layout, course_id=course_id, lecture_id=lecture_id)
    assert revision is not None
    design_target = target(source_refs=(source_path,))
    store = PracticeDesignStore(layout)
    design = store.save_proposal(
        course_id=course_id,
        lecture_id=lecture_id,
        source_revision=revision,
        proposal=proposal().model_copy(update={"targets": (design_target,)}),
        review=passing_review(),
        source=source_document(source_path),
        allowed_source_paths=(source_path,),
        expected_design_revision=None,
        expected_design_approval=None,
        expected_design_review=None,
    )
    store.approve(
        course_id=course_id,
        lecture_id=lecture_id,
        source_revision=revision,
        design_revision=design.revision,
        approved_by="prof01",
    )


def approved_design_document(
    layout: StorageLayout,
    document: CanvasDocument,
    *,
    source_revision: str,
    source_path: str,
) -> tuple[CanvasDocument, PracticeDesign]:
    baseline = next(
        (
            block.text
            for section in document.sections
            for block in section.blocks
            if block.type == "checkpoint" and block.text
        ),
        "Explain the source-grounded mechanism.",
    )
    design_target = target(
        id="practice-target",
        baseline_task=baseline,
        independent_exit_task="Solve a parallel source-grounded task independently.",
        delayed_transfer_task="Solve a changed source-grounded transfer task independently.",
        source_refs=(source_path,),
    )
    design = PracticeDesign.create(
        course_id=document.course_id,
        lecture_id=document.lecture_id,
        lecture_title=document.title,
        objective="Apply the approved source-grounded reasoning independently.",
        planning_context=proposal().planning_context,
        source_revision=source_revision,
        targets=(design_target,),
    )
    store = PracticeDesignStore(layout)
    current = store.read(course_id=document.course_id, lecture_id=document.lecture_id)
    if current is not None:
        design = store.require_approved(
            course_id=document.course_id,
            lecture_id=document.lecture_id,
            source_revision=source_revision,
        )
    else:
        stored = store.save_proposal(
            course_id=document.course_id,
            lecture_id=document.lecture_id,
            source_revision=source_revision,
            proposal=PracticeDesignProposal(
                lecture_title=design.lecture_title,
                objective=design.objective,
                planning_context=design.planning_context,
                targets=design.targets,
            ),
            review=passing_review(),
            source=source_document(source_path),
            allowed_source_paths=(source_path,),
            expected_design_revision=None,
            expected_design_approval=None,
            expected_design_review=None,
        )
        design = store.approve(
            course_id=document.course_id,
            lecture_id=document.lecture_id,
            source_revision=source_revision,
            design_revision=stored.revision,
            approved_by="professor",
        )
    first = document.sections[0]
    blocks = [
        *first.blocks,
        CanvasBlock(
            id=f"practice-{design.targets[0].id}",
            type="checkpoint",
            text=design.targets[0].baseline_task,
        ),
    ]
    return document.model_copy(
        update={"sections": [first.model_copy(update={"blocks": blocks}), *document.sections[1:]]}
    ), design
