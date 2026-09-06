from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.course_practice_design_evidence import PracticeSourceAnchor
from practice_design_test_helpers import practice_design_for_canvas
from practice_design_review_test_helpers import source_document


def test_support_packet_contains_exact_baseline_evidence_but_not_hidden_tasks():
    from lecturepilot.course_canvas_practice_support import practice_support_evidence

    design = practice_design_for_canvas(source_document())
    target = design.targets[0].model_copy(
        update={
            "baseline_task_anchor": PracticeSourceAnchor(
                source_path="lecture-01.md", excerpt="Later-page distinction."
            ),
            "delayed_transfer_task_anchor": PracticeSourceAnchor(
                source_path="lecture-01.md", excerpt="Unlabeled inputs support clustering."
            ),
        }
    )
    packet = practice_support_evidence((target,))
    assert "Later-page distinction." in packet
    assert "Unlabeled inputs support clustering." in packet
    assert "lecture-01.md" in packet
    assert target.independent_exit_task not in packet
    assert target.delayed_transfer_task not in packet


def test_quality_review_receives_owned_cross_section_evidence_without_mutating_source():
    from lecturepilot.course_canvas_practice_support import source_for_practice_review
    from lecturepilot.course_canvas_quality_prompt import compact_quality_evidence

    source = source_document()
    design = practice_design_for_canvas(source)
    original = source.model_dump_json()
    section = source.sections[0].model_copy(
        update={
            "blocks": [
                CanvasBlock(
                    id=f"practice-{design.targets[0].id}",
                    type="checkpoint",
                    text=design.targets[0].baseline_task,
                ),
            ]
        }
    )
    candidate = source.model_copy(update={"sections": [section]})
    evidence = source_for_practice_review(source, candidate, design)
    prompt = compact_quality_evidence(evidence, candidate)
    assert "APPROVED TASK SUPPORTING SOURCE" in prompt
    assert source.model_dump_json() == original
