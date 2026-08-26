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
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.course_practice_design_store import PracticeDesignStore
from lecturepilot.storage_layout import StorageLayout


def proposal() -> PracticeDesignProposal:
    return PracticeDesignProposal(
        lecture_title="Practice design",
        objective="Derive the conclusion independently from the cited evidence.",
        targets=[
            PracticeTarget(
                id="derive-conclusion",
                title="Derive a conclusion",
                outcome="Derive a justified conclusion from the given evidence.",
                baseline_task="Derive the conclusion from the stated evidence and justify the reasoning.",
                independent_exit_task="Derive a conclusion from a parallel evidence set and justify it.",
                delayed_transfer_task="Derive a conclusion after the surface details change and justify it.",
                evidence_criteria=[
                    PracticeEvidenceCriterion(
                        id="cite-evidence",
                        description="Cites the relevant evidence.",
                    )
                ],
                misconceptions=[
                    PracticeMisconception(
                        id="ignore-evidence",
                        description="States a conclusion without evidence.",
                        diagnostic_cue="The response omits a source-grounded reason.",
                    )
                ],
                hint_ladder=[PracticeHint(level="prompt", content="Identify the key evidence.")],
                review_after_days=7,
                source_refs=["lecture-01.md"],
            )
        ],
    )


def target(**changes: object) -> PracticeTarget:
    return PracticeTarget(**{**proposal().targets[0].model_dump(), **changes})


def document(task: str) -> SimpleNamespace:
    block = SimpleNamespace(id="practice-derive-conclusion", type="checkpoint", text=task)
    section = SimpleNamespace(source_ref="lecture-01.md", blocks=[block])
    return SimpleNamespace(sections=[section])


def canvas_with_practice_design(document: CanvasDocument) -> tuple[CanvasDocument, PracticeDesign]:
    design = practice_design_for_canvas(document)
    baseline_task = design.targets[0].baseline_task
    first = document.sections[0]
    return (
        document.model_copy(
            update={
                "sections": [
                    first.model_copy(
                        update={
                            "blocks": [
                                *first.blocks,
                                CanvasBlock(
                                    id="practice-derive-conclusion",
                                    type="checkpoint",
                                    text=baseline_task,
                                ),
                            ]
                        }
                    ),
                    *document.sections[1:],
                ]
            }
        ),
        design,
    )


def practice_design_for_canvas(document: CanvasDocument) -> PracticeDesign:
    baseline_task = "Derive the conclusion from the stated evidence and justify the reasoning."
    design_target = target(
        baseline_task=baseline_task,
        independent_exit_task="Derive a conclusion from a parallel evidence set and justify it.",
        delayed_transfer_task="Derive a conclusion after the surface details change and justify it.",
        source_refs=(document.sections[0].source_ref or document.source_ref,),
    )
    design = PracticeDesign.create(
        course_id=document.course_id,
        lecture_id=document.lecture_id,
        lecture_title=document.title,
        objective="Derive the conclusion independently from the cited evidence.",
        source_revision="a" * 64,
        targets=(design_target,),
    )
    return design


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
    target = proposal().targets[0].model_copy(update={"source_refs": (source_path,)})
    store = PracticeDesignStore(layout)
    design = store.save_proposal(
        course_id=course_id,
        lecture_id=lecture_id,
        source_revision=revision,
        proposal=proposal().model_copy(update={"targets": (target,)}),
        allowed_source_paths=(source_path,),
        expected_design_revision=None,
        expected_design_approval=None,
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
        source_revision=source_revision,
        targets=(design_target,),
    )
    store = PracticeDesignStore(layout)
    stored = store.save_proposal(
        course_id=document.course_id,
        lecture_id=document.lecture_id,
        source_revision=source_revision,
        proposal=PracticeDesignProposal(
            lecture_title=design.lecture_title,
            objective=design.objective,
            targets=design.targets,
        ),
        allowed_source_paths=(source_path,),
        expected_design_revision=None,
        expected_design_approval=None,
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
        CanvasBlock(id="practice-practice-target", type="checkpoint", text=baseline),
    ]
    return document.model_copy(
        update={"sections": [first.model_copy(update={"blocks": blocks}), *document.sections[1:]]}
    ), design
