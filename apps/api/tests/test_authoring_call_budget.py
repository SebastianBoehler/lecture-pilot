"""Pin the canvas authoring model-call budget for a four-goal, five-section lecture.

Before: 5 section writes + 5 per-section critic calls (+ a checkpoint judge per objection),
up to 5 repairs and up to 5 re-reviews, then a full re-run after a design conflict.
Now: 5 writes + 1 critic call, at most one repair per flagged section, no re-review, and only
sections whose inputs a teaching repair changed are written again.
"""

import pytest

from lecturepilot.authoring.authoring_job import run_authoring_job
from lecturepilot.authoring.authoring_models import AuthoringDesignConflict
from authoring_lecture_fixture import (
    SECTION_COUNT,
    ScriptedAuthor,
    ScriptedCritic,
    lecture_design,
    lecture_job,
)


def flag_every_section(document, checkpoints):
    return [
        {"section_id": s.id, "reason": "Link the rule to the claim."} for s in document.sections
    ]


def conflict_on_goal_2(document, checkpoints):
    section = next(s for s in document.sections if s.id == "learning-topic-2")
    return [
        {
            "section_id": section.id,
            "block_id": "practice-goal-2",
            "reason": "The approved task omits the rule the rubric requires.",
            "decision": "design_conflict",
            "evidence_ids": ["goal-2:e0"],
        }
    ]


async def test_happy_path_writes_each_section_and_reviews_the_lecture_once(tmp_path):
    critic, author = ScriptedCritic(), ScriptedAuthor()
    result = await run_authoring_job(lecture_job(tmp_path / "job", critic), model=author.model())

    assert len(author.writes) == SECTION_COUNT and author.repairs == []
    assert len(critic.reviewed) == 1 and len(critic.reviewed[0]) == SECTION_COUNT
    assert result.metrics.model_requests == SECTION_COUNT
    assert result.metrics.quality_reviews == 1
    assert len(author.writes) + len(critic.reviewed) == 6  # was 10 (5 writes + 5 critics)
    assert not result.document.warnings


async def test_worst_path_repairs_each_flagged_section_once_without_rereview(tmp_path):
    critic, author = ScriptedCritic(flag_every_section), ScriptedAuthor()
    result = await run_authoring_job(lecture_job(tmp_path / "job", critic), model=author.model())

    assert sorted(author.repairs) == sorted(author.writes)
    assert len(critic.reviewed) == 1
    total = len(author.writes) + len(author.repairs) + len(critic.reviewed)
    assert total == 11  # was 20 (5 writes + 5 critics + 5 repairs + 5 re-reviews)
    assert sum("repaired once, not re-checked" in w for w in result.document.warnings) == 5


async def test_resumed_job_finishes_pending_repairs_without_another_review(tmp_path):
    critic = ScriptedCritic(flag_every_section)
    author, calls = ScriptedAuthor(), []

    def interrupted(messages, info):
        calls.append(messages)
        if author.repairs:
            raise RuntimeError("worker stopped")
        return author.respond(messages, info)

    from pydantic_ai.models.function import FunctionModel

    with pytest.raises(RuntimeError, match="worker stopped"):
        await run_authoring_job(
            lecture_job(tmp_path / "job", critic), model=FunctionModel(interrupted)
        )
    done = list(author.repairs)
    resumed = ScriptedAuthor()
    result = await run_authoring_job(lecture_job(tmp_path / "job", critic), model=resumed.model())

    assert len(critic.reviewed) == 1
    assert resumed.writes == []
    assert sorted(done + resumed.repairs) == sorted(author.writes)
    assert result.metrics.resumes == 1


async def test_design_conflict_regenerates_only_sections_whose_targets_changed(tmp_path):
    first_critic, first_author = ScriptedCritic(conflict_on_goal_2), ScriptedAuthor()
    with pytest.raises(AuthoringDesignConflict, match="practice-goal-2"):
        await run_authoring_job(
            lecture_job(tmp_path / "old", first_critic), model=first_author.model()
        )
    assert len(first_author.writes) == SECTION_COUNT and len(first_critic.reviewed) == 1

    # The single teaching repair changed goal 2 only; the draft binds to the new revision.
    repaired = lecture_design(changed_goal=2)
    critic, author = ScriptedCritic(), ScriptedAuthor()
    job = lecture_job(
        tmp_path / "new",
        critic,
        design=repaired,
        reuse_root=tmp_path / "old",
        escalate_design_conflicts=False,
    )
    result = await run_authoring_job(job, model=author.model())

    assert author.writes == ["/draft/topic-2.md"]
    assert result.metrics.reused_sections == SECTION_COUNT - 1
    assert len(critic.reviewed) == 1
    checkpoint = next(
        b for s in result.document.sections for b in s.blocks if b.id == "practice-goal-2"
    )
    assert checkpoint.text == repaired.targets[1].baseline_task
    # 5 + 1 before the conflict, then 1 rewrite + 1 critic (was a full 5 + 5 re-run).
    assert len(author.writes) + len(critic.reviewed) == 2


async def test_changed_objective_regenerates_every_section(tmp_path):
    await run_authoring_job(
        lecture_job(tmp_path / "old", ScriptedCritic()), model=ScriptedAuthor().model()
    )
    design = lecture_design().model_copy(update={"objective": "A changed lecture objective."})
    author = ScriptedAuthor()
    job = lecture_job(
        tmp_path / "new", ScriptedCritic(), design=design, reuse_root=tmp_path / "old"
    )
    result = await run_authoring_job(job, model=author.model())
    assert len(author.writes) == SECTION_COUNT
    assert result.metrics.reused_sections == 0
