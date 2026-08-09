from importlib import import_module

from lecturepilot.learning_map import LearningMap, LearningMapGate, LearningMapNode
from lecturepilot.models import QualityGateDecision, QualityGateStatus


def _map(first_criterion_description: str = "Explain the first concept.") -> LearningMap:
    gates = [
        LearningMapGate.create(
            id="lecture-14-first-check",
            concept_id="first-section",
            title="First check",
            prompt="Explain the first concept.",
            evidence_criteria=[
                {"id": "first-explanation", "description": first_criterion_description}
            ],
            transfer_prompt="Apply the first concept to a changed case.",
            review_after_days=2,
            section_id="first-section",
            source_ref=None,
        ),
        LearningMapGate.create(
            id="lecture-14-focused-check",
            concept_id="focused-section",
            title="Focused check",
            prompt="Explain the focused concept.",
            evidence_criteria=[
                {"id": "focused-explanation", "description": "Explain the focused concept."}
            ],
            transfer_prompt="Apply the focused concept to a changed case.",
            review_after_days=2,
            section_id="focused-section",
            source_ref=None,
        ),
    ]
    return LearningMap.create(
        course_id="course",
        lecture_id="lecture-14",
        title="Lecture 14",
        objective="Explain and apply both concepts independently.",
        nodes=[
            LearningMapNode(
                id="first-section",
                title="First",
                lecture_id="lecture-14",
                section_id="first-section",
                source_ref=None,
                prerequisites=[],
                gate_ids=["lecture-14-first-check"],
                quiz_ids=[],
            ),
            LearningMapNode(
                id="focused-section",
                title="Focused",
                lecture_id="lecture-14",
                section_id="focused-section",
                source_ref=None,
                prerequisites=["first-section"],
                gate_ids=["lecture-14-focused-check"],
                quiz_ids=[],
            ),
        ],
        gates=gates,
    )


def _select(learning_map: LearningMap | None = None, **kwargs):
    return import_module("lecturepilot.learning_gate_selector").select_active_gate(
        learning_map or _map(), **kwargs
    )


def test_selector_preserves_later_lecture_checkpoint_id() -> None:
    selected = _select(focused_section_id="focused-section")

    assert selected is not None
    assert selected.id == "lecture-14-focused-check"


def test_selector_skips_passed_gate_and_selects_next_open_gate() -> None:
    learning_map = _map()
    selected = _select(
        learning_map,
        focused_section_id="first-section",
        latest_decisions={
            "lecture-14-first-check": QualityGateDecision(
                gate_id="lecture-14-first-check",
                gate_revision=learning_map.gates[0].revision,
                status=QualityGateStatus.PASSED,
                reason="Complete evidence.",
                evidence_ids=["first-evidence"],
                missing_evidence_ids=[],
            )
        },
    )

    assert selected is not None
    assert selected.id == "lecture-14-focused-check"


def test_selector_reopens_passed_gate_after_contract_revision_changes() -> None:
    previous_map = _map()
    revised_map = _map("Explain the first concept and name its boundary.")
    assert previous_map.gates[0].revision != revised_map.gates[0].revision

    selected = _select(
        revised_map,
        focused_section_id="first-section",
        latest_decisions={
            "lecture-14-first-check": QualityGateDecision(
                gate_id="lecture-14-first-check",
                gate_revision=previous_map.gates[0].revision,
                status=QualityGateStatus.PASSED,
                reason="Complete evidence for the old contract.",
                evidence_ids=["first-evidence"],
                missing_evidence_ids=[],
            )
        },
    )

    assert selected is not None
    assert selected.id == "lecture-14-first-check"


def test_selector_prefers_valid_requested_gate_over_current_focus() -> None:
    selected = _select(
        requested_gate_id="lecture-14-first-check",
        focused_section_id="focused-section",
    )

    assert selected is not None
    assert selected.id == "lecture-14-first-check"


def test_selector_resumes_pending_gate_before_first_open_gate() -> None:
    selected = _select(
        latest_decisions={
            "lecture-14-focused-check": QualityGateDecision(
                gate_id="lecture-14-focused-check",
                gate_revision=_map().gates[1].revision,
                status=QualityGateStatus.NEEDS_EVIDENCE,
                reason="Needs the mechanism.",
                evidence_ids=[],
                missing_evidence_ids=["focused-evidence"],
            )
        }
    )

    assert selected is not None
    assert selected.id == "lecture-14-focused-check"
