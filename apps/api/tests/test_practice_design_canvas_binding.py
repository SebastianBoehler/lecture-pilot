import json
from pathlib import Path

import pytest

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_canvas_store import InvalidCanvasDraftError
from lecturepilot.course_practice_design_binding import read_practice_design_binding
from lecturepilot.course_practice_design_models import (
    PracticeDesign,
    PracticeDesignProposal,
    PracticeDesignUpdate,
)
from lecturepilot.course_practice_design_store import PracticeDesignStore
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.course_practice_design_validation import (
    PracticeDesignValidationError,
    validate_learning_map_practice_contract,
)
from lecturepilot.learning_map import LearningMapEvidenceCriterion, build_learning_map
from practice_design_test_helpers import passing_review, source_document, target


COURSE_ID = "practice-course"
LECTURE_ID = "lecture-01"
SOURCE_REVISION = "a" * 64


def test_bound_draft_writes_exact_practice_gate_and_binding(tmp_path: Path) -> None:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    design = _approved_design(workspace)
    document = _document(design)

    workspace.write_course_canvas_draft(
        document,
        expected_source_revision=design.source_revision,
        practice_design=design,
    )

    draft_dir = workspace.course_canvas_store.draft_path(COURSE_ID, LECTURE_ID)
    binding = read_practice_design_binding(draft_dir)
    learning_map = workspace.course_canvas_store.learning_map(
        course_id=COURSE_ID, lecture_id=LECTURE_ID, draft=True
    )

    assert binding.source_revision == design.source_revision
    assert binding.practice_design_revision == design.revision
    assert learning_map is not None
    assert learning_map.objective == design.objective
    assert learning_map.gates[0].practice_target_id == design.targets[0].id
    assert learning_map.gates[0].prompt == design.targets[0].baseline_task
    assert [item.id for item in learning_map.gates[0].evidence_criteria] == [
        item.id for item in design.targets[0].evidence_criteria
    ]
    assert learning_map.gates[0].independent_exit_task == design.targets[0].independent_exit_task
    assert learning_map.gates[0].transfer_prompt == design.targets[0].delayed_transfer_task
    assert learning_map.gates[0].review_after_days == design.targets[0].review_after_days


@pytest.mark.parametrize(
    "checkpoint_id",
    ["ordinary-checkpoint", "practice-unknown-target"],
)
def test_bound_draft_rejects_missing_or_unknown_target_checkpoint(
    tmp_path: Path, checkpoint_id: str
) -> None:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    design = _approved_design(workspace)
    document = _document(design, checkpoint_id=checkpoint_id)

    with pytest.raises(InvalidCanvasDraftError, match="practice"):
        workspace.write_course_canvas_draft(
            document,
            expected_source_revision=design.source_revision,
            practice_design=design,
        )

    assert not workspace.course_canvas_store.draft_path(COURSE_ID, LECTURE_ID).exists()


def test_shared_validator_rejects_mutated_target_criterion(tmp_path: Path) -> None:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    design = _approved_design(workspace)
    learning_map = build_learning_map(_document(design), design)
    mutated = learning_map.model_copy(
        update={
            "gates": [
                learning_map.gates[0].model_copy(
                    update={
                        "evidence_criteria": [
                            LearningMapEvidenceCriterion(
                                id="different-criterion", description="Mutated criterion."
                            )
                        ]
                    }
                )
            ]
        }
    )

    with pytest.raises(PracticeDesignValidationError, match="differs"):
        validate_learning_map_practice_contract(mutated, design)


def test_shared_validator_rejects_mutated_independent_exit_task(tmp_path: Path) -> None:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    design = _approved_design(workspace)
    learning_map = build_learning_map(_document(design), design)
    mutated = learning_map.model_copy(
        update={
            "gates": [
                learning_map.gates[0].model_copy(
                    update={"independent_exit_task": "A mutated independent exit."}
                )
            ]
        }
    )

    with pytest.raises(PracticeDesignValidationError, match="differs"):
        validate_learning_map_practice_contract(mutated, design)


def test_draft_learning_map_rejects_superseded_practice_design(tmp_path: Path) -> None:
    workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces", material_root=tmp_path / "materials"
    )
    design = _approved_design(workspace)
    workspace.write_course_canvas_draft(
        _document(design),
        expected_source_revision=design.source_revision,
        practice_design=design,
    )
    PracticeDesignStore(workspace.layout).update(
        course_id=design.course_id,
        lecture_id=design.lecture_id,
        current_source_revision=design.source_revision,
        update=PracticeDesignUpdate(
            source_revision=design.source_revision,
            practice_design_revision=design.revision,
            lecture_title=design.lecture_title,
            objective="Revised approved objective.",
            planning_context=design.planning_context,
            targets=design.targets,
        ),
        source=source_document("lecture.md"),
        allowed_source_paths=("lecture.md",),
    )

    with pytest.raises(InvalidCanvasDraftError, match="Stored canvas draft is invalid"):
        workspace.course_canvas_store.learning_map(
            course_id=COURSE_ID, lecture_id=LECTURE_ID, draft=True
        )


def _approved_design(workspace: CanvasWorkspace) -> PracticeDesign:
    _write_source_manifest(workspace)
    revision = lecture_source_revision(workspace.layout, course_id=COURSE_ID, lecture_id=LECTURE_ID)
    assert revision is not None
    design = PracticeDesign.create(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        lecture_title="Practice lecture",
        objective="Derive the conclusion independently from the cited evidence.",
        planning_context={
            "learner_level": "Undergraduate learners in this lecture.",
            "prerequisites": ["Interpret the supplied evidence."],
            "time_budget_minutes": 30,
            "allowed_aids": ["Course notes"],
            "assessment_conditions": "Complete each assessment individually.",
            "insufficiencies": [],
        },
        source_revision=revision,
        targets=[
            target(
                source_refs=("lecture.md",),
                baseline_task="Derive the conclusion from the stated evidence and justify it.",
                independent_exit_task="Derive a conclusion from parallel evidence and justify it.",
                delayed_transfer_task="Derive a conclusion after details change and justify it.",
            )
        ],
    )
    store = PracticeDesignStore(workspace.layout)
    proposed = PracticeDesignProposal(
        lecture_title=design.lecture_title,
        objective=design.objective,
        planning_context=design.planning_context,
        targets=design.targets,
    )
    stored = store.save_proposal(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        source_revision=revision,
        proposal=proposed,
        review=passing_review(),
        source=source_document("lecture.md"),
        allowed_source_paths=("lecture.md",),
        expected_design_revision=None,
        expected_design_approval=None,
        expected_design_review=None,
    )
    return store.approve(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        source_revision=revision,
        design_revision=stored.revision,
        approved_by="professor",
    )


def _document(design: PracticeDesign, *, checkpoint_id: str | None = None) -> CanvasDocument:
    target = design.targets[0]
    return CanvasDocument(
        id=f"{COURSE_ID}-{LECTURE_ID}",
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        title=design.lecture_title,
        source_kind="generated",
        source_ref="lecture.md",
        workspace_path="course/index.md",
        sections=[
            CanvasSection(
                id="evidence",
                title="Evidence",
                source_ref="lecture.md#evidence",
                blocks=[
                    CanvasBlock(id="context", type="paragraph", text="Grounded context."),
                    CanvasBlock(
                        id=checkpoint_id or f"practice-{target.id}",
                        type="checkpoint",
                        text=target.baseline_task,
                    ),
                ],
            )
        ],
    )


def _write_source_manifest(workspace: CanvasWorkspace) -> None:
    path = workspace.layout.lecture_source_manifest_path(COURSE_ID, LECTURE_ID)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "course_id": COURSE_ID,
                "lecture_id": LECTURE_ID,
                "files": [{"path": "lecture.md", "sha256": "a" * 64}],
            }
        ),
        encoding="utf-8",
    )
