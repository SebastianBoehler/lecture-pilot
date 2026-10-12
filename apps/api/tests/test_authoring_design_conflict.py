import pytest
from pydantic_ai.models.function import FunctionModel

from lecturepilot.authoring.authoring_job import run_authoring_job
from lecturepilot.authoring.authoring_models import AuthoringDesignConflict
from lecturepilot.authoring.course_canvas_quality import CanvasQualityReviewer
from authoring_test_helpers import markdown
from test_authoring_job import authoring_job


def seeded_job(tmp_path, decision, *, evidence=None, block=None):
    """A drafted lecture whose single critic call objects to the approved checkpoint."""
    job = authoring_job(tmp_path)
    job.candidate = job.source.model_copy(deep=True)
    job.candidate.sections[0].source_section_id = "topic"
    target = job.design.targets[0]
    reviews = []

    class Critic:
        async def complete_review(self, *, checkpoints, **kwargs):
            reviews.append(sorted(checkpoints))
            return {
                "issues": [
                    {
                        "section_id": "topic",
                        "block_id": block or "practice-" + target.id,
                        "reason": "The objection to the approved checkpoint.",
                        "decision": decision,
                        "evidence_ids": [f"{target.id}:e0"] if evidence is None else evidence,
                    }
                ]
            }

    job.reviewer = CanvasQualityReviewer(Critic())
    return job, reviews


def keep_draft(messages, info):
    prompt = str(messages[0].parts[-1].content)
    return markdown(prompt.split("Current draft:\n")[1].split("\nNotes")[0])


async def test_verified_design_conflict_escalates_without_rewriting_the_task(tmp_path):
    job, reviews = seeded_job(tmp_path, "design_conflict")

    def respond(messages, info):
        raise AssertionError("A confirmed design conflict needs no section rewrite.")

    with pytest.raises(AuthoringDesignConflict, match="practice-" + job.design.targets[0].id):
        await run_authoring_job(job, model=FunctionModel(respond))
    # The critic saw the approved contract and classified it in the same single call.
    assert reviews == [["practice-" + job.design.targets[0].id]]


async def test_dismissed_checkpoint_objection_does_not_veto_completion(tmp_path):
    job, reviews = seeded_job(tmp_path, "dismiss")
    result = await run_authoring_job(
        job, model=FunctionModel(lambda messages, info: pytest.fail("no rewrite needed"))
    )
    assert result.document.sections[0].blocks[0].text == job.design.targets[0].baseline_task
    assert not result.document.warnings
    assert len(reviews) == 1


async def test_missing_teaching_is_repaired_once_and_not_reviewed_again(tmp_path):
    job, reviews = seeded_job(tmp_path, "repair_section")
    calls = []

    def respond(messages, info):
        calls.append(messages)
        assert "The objection to the approved checkpoint." in str(messages)
        return keep_draft(messages, info)

    result = await run_authoring_job(job, model=FunctionModel(respond))
    assert len(calls) == 1
    assert len(reviews) == 1
    assert result.document.sections[0].blocks[0].text == job.design.targets[0].baseline_task
    assert any("repaired once, not re-checked" in w for w in result.document.warnings)


async def test_repeat_conflict_after_teaching_repair_becomes_a_draft_warning(tmp_path):
    job, reviews = seeded_job(tmp_path, "design_conflict")
    job.escalate_design_conflicts = False
    result = await run_authoring_job(
        job, model=FunctionModel(lambda messages, info: pytest.fail("approved task is fixed"))
    )
    assert result.document.sections[0].blocks[0].text == job.design.targets[0].baseline_task
    assert any("open note(s) on approved checkpoints" in w for w in result.document.warnings)


@pytest.mark.parametrize(
    "evidence, block",
    [([], None), (["unknown:e0"], None), (None, "evidence")],
    ids=["no-evidence", "foreign-evidence", "not-a-checkpoint"],
)
async def test_unverifiable_conflict_stays_a_section_note(tmp_path, evidence, block):
    job, reviews = seeded_job(tmp_path, "design_conflict", evidence=evidence, block=block)
    calls = []

    def respond(messages, info):
        calls.append(messages)
        return keep_draft(messages, info)

    result = await run_authoring_job(job, model=FunctionModel(respond))
    assert len(calls) == 1
    assert any("repaired once, not re-checked" in w for w in result.document.warnings)
