from datetime import timedelta

import pytest
from pydantic import ValidationError

from lecturepilot.coaching_progress import CoachingProgressStore
from lecturepilot.coaching_transitions import derive_next_transition
from lecturepilot.learning_map import LearningMapGate
from lecturepilot.models import QualityGateDecision, QualityGateStatus
from lecturepilot.scaffold_policy import scaffold_policy_for_assessment_stage
from lecturepilot.storage_layout import StorageLayout
from practice_design_test_helpers import target
from practice_gate_coaching_test_helpers import IDS, NOW, practice_gate


def targeted_gate():
    payload = practice_gate().model_dump(exclude={"revision"})
    payload["evidence_criteria"].append(
        {"id": "application", "description": "Applies the boundary to the changed case."}
    )
    for hint, evidence_id in zip(payload["hint_ladder"], ["boundary", "application"]):
        hint["evidence_ids"] = [evidence_id]
    return LearningMapGate.create(**payload)


def transition(gate, missing, exposed=()):
    return derive_next_transition(
        gate,
        current_stage="diagnostic",
        status=QualityGateStatus.NEEDS_EVIDENCE,
        missing_evidence_ids=missing,
        exposed_hint_levels=exposed,
    )


@pytest.mark.parametrize("missing,level", [(["boundary"], "prompt"), (["application"], "cue")])
def test_support_addresses_the_observed_gap(missing, level):
    result = transition(targeted_gate(), missing)
    assert result.check.assistance.level == level


def test_multiple_gaps_use_least_assistance_and_do_not_repeat_or_use_irrelevant_help():
    gate = targeted_gate()
    assert transition(gate, ["boundary", "application"]).check.assistance.level == "prompt"
    assert transition(gate, ["application"], ["cue"]).check.assistance.level == "none"
    assert transition(gate, []).check.assistance.level == "none"
    with pytest.raises(ValueError, match="Unknown"):
        transition(gate, ["invented"])


@pytest.mark.parametrize("ids", [["unknown"], ["boundary", "boundary"]])
def test_gate_rejects_invalid_hint_bindings(ids):
    payload = targeted_gate().model_dump(exclude={"revision"})
    payload["hint_ladder"][0]["evidence_ids"] = ids
    with pytest.raises(ValidationError, match="evidence"):
        LearningMapGate.create(**payload)


def test_practice_design_validates_bindings_and_preserves_legacy_serialization():
    original = target()
    assert "evidence_ids" not in original.model_dump()["hint_ladder"][0]
    hints = [original.hint_ladder[0].model_dump() | {"evidence_ids": ["cite-evidence"]}]
    assert target(hint_ladder=hints).hint_ladder[0].evidence_ids == ("cite-evidence",)
    hints[0]["evidence_ids"] = ["unknown"]
    with pytest.raises(ValidationError, match="evidence"):
        target(hint_ladder=hints)


def test_binding_changes_gate_revision_and_legacy_gate_round_trips():
    gate = practice_gate()
    assert "evidence_ids" not in gate.model_dump()["hint_ladder"][0]
    assert LearningMapGate.model_validate_json(gate.model_dump_json()) == gate
    payload = gate.model_dump(exclude={"revision"})
    payload["hint_ladder"][0]["evidence_ids"] = ["boundary"]
    assert LearningMapGate.create(**payload).revision != gate.revision


def test_selection_and_reason_survive_reload_then_require_independent_exit(tmp_path):
    gate = targeted_gate()
    store = CoachingProgressStore(StorageLayout(tmp_path))
    store.bind_inline_checkpoint(**IDS, gate=gate, now=NOW)
    for index, missing in enumerate((["application"], [])):
        context = store.context(
            **IDS,
            gate_id=gate.id,
            gate_revision=gate.revision,
            learning_objective="Apply the boundary.",
            now=NOW + timedelta(minutes=index + 1),
        )
        status = QualityGateStatus.NEEDS_EVIDENCE if missing else QualityGateStatus.PASSED
        selected = derive_next_transition(
            gate,
            current_stage=context.pending_check_stage,
            status=status,
            exposed_hint_levels=context.exposed_hint_levels,
            exposed_task_ids=context.exposed_task_ids,
            current_task_id=context.pending_check_task_id,
            missing_evidence_ids=missing,
        )
        store.record_turn(
            **IDS,
            context=context,
            policy=scaffold_policy_for_assessment_stage(
                stage=context.pending_check_stage,
                assistance_level=context.last_assistance_level,
            ),
            decision=QualityGateDecision(
                gate_id=gate.id,
                gate_revision=gate.revision,
                status=status,
                reason="Checks the application criterion.",
                evidence_ids=[c.id for c in gate.evidence_criteria if c.id not in missing],
                missing_evidence_ids=missing,
            ),
            next_check=selected.check,
            gate=gate,
            user_message="My attempt.",
            assistant_message="Assessment recorded.",
            now=NOW + timedelta(minutes=index + 1),
        )
        store = CoachingProgressStore(StorageLayout(tmp_path))
        progress = store.read(**IDS)
        if missing:
            assert progress.pending_check.assistance_content == gate.hint_ladder[1].content
            assert progress.turns[-1].missing_evidence_ids == ["application"]
            assert progress.turns[-1].selected_support_level == "cue"
        else:
            assert progress.pending_check.stage == "independent_exit"
            assert progress.pending_check.assistance_level == "none"
            assert progress.delayed_reviews == {}
            assert not next(iter(progress.goal_evidence.values())).independent


def test_provider_assessment_drives_server_selection():
    from types import SimpleNamespace
    from lecturepilot.model_commands import select_next_check

    gate = targeted_gate()
    turn = SimpleNamespace(
        active_gate=gate,
        coaching_context=SimpleNamespace(
            pending_check_stage="diagnostic",
            exposed_hint_levels=[],
            exposed_task_ids=[],
            pending_check_task_id="baseline",
        ),
    )
    decision = QualityGateDecision(
        gate_id=gate.id,
        gate_revision=gate.revision,
        status=QualityGateStatus.NEEDS_EVIDENCE,
        reason="Application missing.",
        evidence_ids=["boundary"],
        missing_evidence_ids=["application"],
    )
    assert select_next_check(turn, decision).assistance.level == "cue"


def test_learning_map_preserves_binding_and_rejects_changed_approved_binding():
    from lecturepilot.learning_map import build_learning_map, LearningMap
    from lecturepilot.course_practice_design_models import PracticeDesign
    from lecturepilot.course_practice_design_validation import (
        validate_learning_map_practice_contract,
        PracticeDesignValidationError,
    )
    from test_practice_design_canvas_hardening import _design, _generated_document

    original = _design()
    payload = original.model_dump(exclude={"revision"})
    payload["targets"][0]["hint_ladder"][0]["evidence_ids"] = ["cite-evidence"]
    design = PracticeDesign.create(**payload)
    learning_map = build_learning_map(_generated_document(design), design)
    assert learning_map.gates[0].hint_ladder[0].evidence_ids == ["cite-evidence"]
    validate_learning_map_practice_contract(learning_map, design)
    changed = learning_map.gates[0].model_dump(exclude={"revision"})
    changed["hint_ladder"][0]["evidence_ids"] = []
    altered = LearningMap.create(
        **{
            **learning_map.model_dump(exclude={"revision", "gates"}),
            "gates": [LearningMapGate.create(**changed)],
        }
    )
    with pytest.raises(PracticeDesignValidationError, match="differs"):
        validate_learning_map_practice_contract(altered, design)
