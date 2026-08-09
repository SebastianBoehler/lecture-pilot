from importlib import import_module

from lecturepilot.learning_map import LearningMap, LearningMapGate, LearningMapNode
from lecturepilot.models import QualityGateDecision, QualityGateStatus


def _map(first_criterion_description: str = "Explain the first concept.") -> LearningMap:
    return LearningMap(
        course_id="course",
        lecture_id="lecture-14",
        title="Lecture 14",
        nodes=[
            LearningMapNode(
                id="first-section",
                title="First",
                lecture_id="lecture-14",
                section_id="first-section",
                gate_ids=["lecture-14-first-check"],
            ),
            LearningMapNode(
                id="focused-section",
                title="Focused",
                lecture_id="lecture-14",
                section_id="focused-section",
                gate_ids=["lecture-14-focused-check"],
            ),
        ],
        gates=[
            LearningMapGate(
                id="lecture-14-first-check",
                concept_id="first-section",
                title="First check",
                prompt="Explain the first concept.",
                evidence_criteria=[
                    {"id": "first-explanation", "description": first_criterion_description}
                ],
                section_id="first-section",
            ),
            LearningMapGate(
                id="lecture-14-focused-check",
                concept_id="focused-section",
                title="Focused check",
                prompt="Explain the focused concept.",
                evidence_criteria=[
                    {"id": "focused-explanation", "description": "Explain the focused concept."}
                ],
                section_id="focused-section",
            ),
        ],
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
            )
        },
    )

    assert selected is not None
    assert selected.id == "lecture-14-first-check"


def test_selector_reopens_legacy_revisionless_pass() -> None:
    selected = _select(
        focused_section_id="first-section",
        latest_decisions={
            "lecture-14-first-check": QualityGateDecision(
                gate_id="lecture-14-first-check",
                status=QualityGateStatus.PASSED,
                reason="Legacy revisionless pass.",
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
                status=QualityGateStatus.NEEDS_EVIDENCE,
                reason="Needs the mechanism.",
            )
        }
    )

    assert selected is not None
    assert selected.id == "lecture-14-focused-check"
