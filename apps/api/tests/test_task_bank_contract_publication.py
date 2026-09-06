import json

import pytest
from pydantic import ValidationError

from lecturepilot.course_canvas_practice_contract import practice_prompt_instruction
from lecturepilot.course_learning_intent import LearningIntent
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.course_practice_design_review_prompt import practice_design_review_messages
from lecturepilot.course_practice_design_validation import validate_practice_design
from lecturepilot.learning_map import LearningMapGate
from practice_design_test_helpers import proposal, target
from reviewed_task_bank_helpers import with_bank
from test_practice_design_semantic_review import _source
from practice_gate_coaching_test_helpers import practice_gate


def design_for(target):
    return PracticeDesign.create(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision="a" * 64,
        **proposal().model_copy(update={"targets": (target,)}).model_dump(),
    )


def test_legacy_target_and_approved_fixed_target_hashes_are_unchanged():
    legacy = target()
    assert "supplemental_tasks" not in legacy.model_dump(mode="json")
    design = design_for(legacy)
    serialized = design.model_dump_json()
    restored = PracticeDesign.model_validate_json(serialized)
    assert restored.revision == design.revision
    assert restored.model_dump_json() == serialized
    intent = LearningIntent.from_design(design, fixed_target_ids=(legacy.id,))
    intent.require_matches(restored)
    changed = design_for(with_bank(legacy))
    assert changed.revision != design.revision
    with pytest.raises(ValueError, match="professor-fixed"):
        intent.require_matches(changed)


def test_canonical_legacy_gate_retains_known_baseline_revision():
    gate = practice_gate()
    assert gate.revision == "3bdfe529cdbdf01775a2cf0d02ef5de1e539d404667f6c2e937b3349da98ce7d"
    payload = gate.model_dump_json()
    assert "supplemental_tasks" not in payload
    assert LearningMapGate.model_validate_json(payload).model_dump_json() == payload


def test_supplemental_tasks_are_reviewed_but_never_forwarded_to_teaching():
    task = with_bank(target())
    design = design_for(task)
    teaching = practice_prompt_instruction(design)
    review = json.dumps(
        practice_design_review_messages(
            _source(),
            design,
            source_revision="a" * 64,
            allowed_source_paths=("lecture-01.md",),
            catalogue={},
        )
    )
    for hidden in (
        task.independent_exit_task,
        task.delayed_transfer_task,
        *(item.prompt for item in task.supplemental_tasks),
    ):
        assert hidden not in teaching
        assert hidden in review
    assert "numeric assertions" in review


def test_supplemental_task_sources_receive_exact_existing_validation():
    task = with_bank(target())
    payload = task.model_dump(mode="json")
    payload["supplemental_tasks"][0]["source_anchor"]["excerpt"] = "Invented absent quotation."
    from lecturepilot.course_practice_target import PracticeTarget

    bad = PracticeTarget.model_validate(payload)
    with pytest.raises(ValueError, match="verbatim excerpt"):
        validate_practice_design(
            proposal().model_copy(update={"targets": (bad,)}),
            source=_source(),
            allowed_source_paths=("lecture-01.md",),
        )


def test_duplicate_bank_prompt_and_reserved_identity_are_rejected():
    task = with_bank(target())
    payload = task.model_dump(mode="json")
    payload["supplemental_tasks"][0]["prompt"] = task.independent_exit_task
    from lecturepilot.course_practice_target import PracticeTarget

    with pytest.raises(ValidationError, match="differ"):
        PracticeTarget.model_validate(payload)
    payload["supplemental_tasks"][0]["id"] = "independent-exit"
    with pytest.raises(ValidationError, match="canonical"):
        PracticeTarget.model_validate(payload)


def test_assessment_prompt_is_exact_fresh_task_and_uses_published_criteria():
    from lecturepilot.tutor_gate_context import gate_rubric_context
    from test_strict_model_payload import _turn
    from practice_gate_coaching_test_helpers import bank_gate

    gate = bank_gate()
    turn = _turn()
    turn = turn.model_copy(
        update={
            "active_gate": gate,
            "coaching_context": turn.coaching_context.model_copy(
                update={
                    "pending_check_prompt": gate.supplemental_tasks[0].prompt,
                    "pending_check_stage": "independent_exit",
                    "pending_check_task_id": "exit-fresh",
                    "exposed_task_ids": ["baseline", "independent-exit", "exit-fresh"],
                }
            ),
        }
    )
    context = gate_rubric_context(turn)
    assert f"Gate prompt: {gate.supplemental_tasks[0].prompt}" in context
    assert all(criterion.description in context for criterion in gate.evidence_criteria)
