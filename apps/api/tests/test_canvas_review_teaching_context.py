from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.course_canvas_quality_prompt import compact_quality_evidence
from lecturepilot.course_canvas_auto_repair import repair_until_quality_valid
from lecturepilot.course_canvas_quality import CanvasQualityIssue
from lecturepilot.course_canvas_repair_prompt import repair_messages
from test_course_canvas_batched_repair import _documents
from test_course_canvas_batched_repair import _BatchPlanner


async def test_missing_teaching_at_approved_checkpoint_repairs_its_section():
    source, candidate, design = _documents()
    section = candidate.sections[0]
    target = next(b for b in section.blocks if b.id.startswith("practice-"))
    issue = CanvasQualityIssue(
        section_id=section.id,
        block_id=target.id,
        reason="The method needed for this approved task is missing from teaching.",
    )
    planner = _BatchPlanner(reviews=[[]])
    await repair_until_quality_valid(
        planner,
        source=source,
        candidate=candidate,
        section_id=section.id,
        block_id=target.id,
        failure_context="Canvas quality review failed.",
        quality_issues=[issue],
        output_language="en",
        practice_design=design,
    )
    assert planner.repair_calls[0][1] is None


def test_critic_receives_component_teaching_content_not_just_its_caption():
    source, candidate, _ = _documents()
    candidate.sections[0].blocks.append(
        CanvasBlock(
            id="training-roles",
            type="component",
            component_type="process_explorer",
            component_data={
                "steps": [
                    {"title": "Training", "text": "Fit parameters using training data."},
                    {
                        "title": "Validation",
                        "text": "Use held-out validation data to compare settings.",
                    },
                ]
            },
        )
    )
    assert "Fit parameters using training data." in compact_quality_evidence(source, candidate)


def test_targeted_repair_can_read_neighbor_teaching_without_other_assessment_text():
    source, candidate, design = _documents()
    section = candidate.sections[0]
    section.blocks.insert(
        0, CanvasBlock(id="neighbor", type="paragraph", text="An explanation already provided.")
    )
    target = next(b for b in section.blocks if b.id.startswith("practice-"))
    messages = repair_messages(
        source,
        section,
        target,
        "Missing supporting instruction.",
        practice_design=design,
        output_language="en",
    )
    assert "An explanation already provided." in messages[1]["content"]
