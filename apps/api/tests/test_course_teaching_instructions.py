from lecturepilot.course_canvas_quality import _quality_messages
from lecturepilot.course_practice_design_prompt import practice_design_messages
from lecturepilot.course_practice_design_review_prompt import practice_design_review_messages
from practice_design_test_helpers import practice_design_for_canvas
from practice_design_review_test_helpers import source_document
from lecturepilot.practice_evidence_catalogue import evidence_catalogue


def test_canvas_author_receives_teaching_and_media_boundaries(tmp_path) -> None:
    from lecturepilot.authoring_job import _instructions
    from lecturepilot.authoring_workspace import AuthoringWorkspace
    from test_authoring_job import authoring_job

    job = authoring_job(tmp_path)
    workspace = AuthoringWorkspace(job.root, job.source, job.design, job.authorize)
    prompts = [_instructions(job, workspace)]
    for prompt in prompts:
        assert "assessment format from the capability" in prompt
        assert "concept-specific section title" in prompt
        assert "diagnostics before substantive help" in prompt
        assert "neutral source caption" in prompt
        assert "feedback QR slide is not a concept summary" in prompt
        assert "recognition anchor for each section" not in prompt
        assert "checkpoint text is not an explanation" in prompt
        assert "Do not reveal the diagnostic's solution" in prompt
        assert "prediction or principle explanation" in prompt
        assert "prerequisites are missing" in prompt
        assert "Avoid back-to-back quiz and checkpoint blocks" in prompt
        assert "check-context-<target_id>" in prompt
        assert "Never delete, merge, shorten or rewrite approved tasks" in prompt


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
    for prompt in (planner, critic):
        assert "derive consequences from its formulas or definitions" in prompt
        assert "Do not introduce unrelated topics" in prompt


def test_canvas_critic_checks_media_claims_without_claiming_unseen_visual_verification() -> None:
    source = source_document()
    prompt = _quality_messages(source, source)[0]["content"]
    assert "caption/source mismatch as a factual error" in prompt
    assert "do not claim visual verification" in prompt
    assert "missing instruction needed to solve" in prompt
    assert "interaction alone is not evidence" in prompt
    assert "Review assessment flow" in prompt
