from lecturepilot.course_canvas_prompt import planner_messages
from lecturepilot.course_canvas_section_prompt import section_messages
from lecturepilot.course_canvas_quality import _quality_messages
from lecturepilot.course_practice_design_prompt import practice_design_messages
from lecturepilot.course_practice_design_review_prompt import practice_design_review_messages
from practice_design_test_helpers import practice_design_for_canvas
from practice_design_review_test_helpers import source_document
from lecturepilot.practice_evidence_catalogue import evidence_catalogue


def test_both_canvas_writers_receive_the_same_teaching_and_media_boundaries() -> None:
    source = source_document()
    design = practice_design_for_canvas(source)
    prompts = [
        planner_messages(source, design)[0]["content"],
        section_messages(
            source, source.sections[0], practice_design=design, applicable_targets=design.targets
        )[0]["content"],
    ]
    for prompt in prompts:
        assert "assessment format from the capability" in prompt
        assert "concept-specific section title" in prompt
        assert "diagnostics before substantive help" in prompt
        assert "neutral source caption" in prompt
        assert "feedback QR slide is not a concept summary" in prompt
        assert "recognition anchor for each section" not in prompt
        assert "checkpoint text is not an explanation" in prompt
        assert "Do not reveal the diagnostic's solution" in prompt


def test_planner_and_critic_distinguish_capability_from_administrative_recall() -> None:
    source = source_document()
    design = practice_design_for_canvas(source)
    args = {"source_revision": "a" * 64, "allowed_source_paths": ["lecture-01.md"]}
    planner = practice_design_messages(source, **args)[0]["content"]
    critic = practice_design_review_messages(
        source, design, **args, catalogue=evidence_catalogue(source, args["allowed_source_paths"])
    )[0]["content"]
    assert "logistics" in planner
    assert "observable operation" in planner
    assert "fully instantiated tasks" in planner
    assert "optional criteria are enrichment only" in planner
    assert "never infer expertise from attendance" in planner
    assert "solve every concrete task" in planner
    assert "never reuse hidden exit or delayed-transfer givens" in planner
    assert "administrative recall" in critic
    assert "answer-revealing givens" in critic
    assert "work through each numerical example" in critic
    assert "hidden exit or delayed-transfer values" in critic
    assert "after an attempt" in critic
    assert "deducible from supplied formulas" in critic


def test_canvas_critic_checks_media_claims_without_claiming_unseen_visual_verification() -> None:
    source = source_document()
    prompt = _quality_messages(source, source)[0]["content"]
    assert "caption/source mismatch as a factual error" in prompt
    assert "do not claim visual verification" in prompt
    assert "missing instruction needed to solve" in prompt
