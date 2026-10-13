"""A professor change request regenerates only its sections through the bounded workflow."""

import json

import pytest
from pydantic_ai.models.function import FunctionModel

from authoring_lecture_fixture import ScriptedAuthor, ScriptedCritic, lecture_job
from authoring_test_helpers import current_draft, drafted_path, is_repair, markdown
from lecturepilot.authoring.authoring_job import run_authoring_job
from lecturepilot.authoring.canvas_change_authoring import (
    GOALS_CHANGE_MESSAGE,
    CanvasChangeRequestError,
    run_change_job,
)

INSTRUCTION = "Add a worked example after the explanation."


async def _base(tmp_path):
    result = await run_authoring_job(
        lecture_job(tmp_path / "base", ScriptedCritic()), model=ScriptedAuthor().model()
    )
    return result.document


class ChangeAuthor:
    """Answers the selection call, change calls and repairs; records every model call."""

    def __init__(self, *, selection=("learning-topic-3",), checkpoint_text=None):
        self.selection, self.checkpoint_text = selection, checkpoint_text
        self.calls: list[str] = []

    def respond(self, messages, info):
        prompt = str(messages[0].parts[-1].content)
        if "Sections of the lecture" in prompt:
            self.calls.append("select")
            sections = [{"section_id": s, "reason": "Names the example."} for s in self.selection]
            return markdown(json.dumps({"sections": sections}))
        path = drafted_path(messages)
        self.calls.append(("repair " if is_repair(messages) else "change ") + path)
        draft = current_draft(messages) if is_repair(messages) else _change_draft(prompt)
        addition = (
            '\n<!-- block id="practice-goal-2" type="checkpoint" -->\n'
            f":::checkpoint Apply it\n{self.checkpoint_text}\n:::\n"
            if self.checkpoint_text
            else '\n<!-- block id="worked-example" type="paragraph" -->\n'
            "Worked example: the stated rule applied to the evidence item.\n"
        )
        return markdown(draft.rstrip() + "\n" + addition)

    def model(self):
        return FunctionModel(self.respond)


def _change_draft(prompt):
    return prompt.split("Current draft:\n", 1)[1].split("\nProfessor change request:", 1)[0]


async def test_named_sections_change_and_every_other_section_stays_identical(tmp_path):
    base = await _base(tmp_path)
    author, critic = ChangeAuthor(), ScriptedCritic()

    result = await run_change_job(
        lecture_job(tmp_path / "change", critic),
        model=author.model(),
        base=base,
        instruction=INSTRUCTION,
        section_ids=("learning-topic-2",),
    )

    document = result.document
    assert author.calls == ["change /draft/topic-2.md"]
    assert critic.reviewed == [["learning-topic-2"]]
    for before, after in zip(base.sections, document.sections, strict=True):
        if before.id == "learning-topic-2":
            assert "worked-example" in [block.id for block in after.blocks]
            assert after.blocks[0] == before.blocks[0]  # The approved checkpoint is unchanged.
        else:
            assert after == before
    assert result.section_ids == ("learning-topic-2",)
    assert result.selection == "professor"


async def test_change_request_prompt_carries_the_instruction_as_untrusted_data(tmp_path):
    base = await _base(tmp_path)
    prompts = []
    author = ChangeAuthor()

    def respond(messages, info):
        prompts.append(str(messages[0].parts[-1].content))
        return author.respond(messages, info)

    await run_change_job(
        lecture_job(tmp_path / "change", ScriptedCritic()),
        model=FunctionModel(respond),
        base=base,
        instruction=INSTRUCTION,
        section_ids=("learning-topic-1",),
    )
    assert f"Professor change request: {INSTRUCTION}" in prompts[0]
    assert "independent_exit_task" not in prompts[0]
    assert "Justify a parallel claim" not in prompts[0]  # Hidden exit tasks never leave.


async def test_automatic_selection_is_one_bounded_call_over_titles(tmp_path):
    base = await _base(tmp_path)
    author, critic = (
        ChangeAuthor(selection=("learning-topic-3", "learning-topic-5")),
        (ScriptedCritic()),
    )

    result = await run_change_job(
        lecture_job(tmp_path / "change", critic),
        model=author.model(),
        base=base,
        instruction=INSTRUCTION,
        section_ids=(),
    )

    assert author.calls[0] == "select"
    assert author.calls.count("select") == 1
    assert sorted(author.calls[1:]) == ["change /draft/topic-3.md", "change /draft/topic-5.md"]
    assert result.selection == "automatic"
    assert result.section_ids == ("learning-topic-3", "learning-topic-5")
    assert result.reasons == {
        "learning-topic-3": "Names the example.",
        "learning-topic-5": "Names the example.",
    }
    unchanged = {"learning-topic-1", "learning-topic-2", "learning-topic-4"}
    for before, after in zip(base.sections, result.document.sections, strict=True):
        assert (after == before) is (before.id in unchanged)


async def test_critic_notes_get_one_repair_and_stay_visible_as_warnings(tmp_path):
    base = await _base(tmp_path)

    def flag(document, checkpoints):
        return [
            {"section_id": s.id, "reason": "Tie the example to the rule."}
            for s in document.sections
        ]

    author, critic = ChangeAuthor(), ScriptedCritic(flag)
    result = await run_change_job(
        lecture_job(tmp_path / "change", critic),
        model=author.model(),
        base=base,
        instruction=INSTRUCTION,
        section_ids=("learning-topic-2",),
    )

    assert author.calls == ["change /draft/topic-2.md", "repair /draft/topic-2.md"]
    assert len(critic.reviewed) == 1
    assert any("repaired once, not re-checked" in w for w in result.document.warnings)
    # Calls: 1 change + 1 critic + 1 repair; nothing outside the named section.
    assert len(author.calls) + len(critic.reviewed) == 3


async def test_altering_an_approved_checkpoint_fails_with_the_goals_message(tmp_path):
    base = await _base(tmp_path)
    author = ChangeAuthor(checkpoint_text="Justify claim 2 without any evidence.")

    with pytest.raises(CanvasChangeRequestError) as raised:
        await run_change_job(
            lecture_job(tmp_path / "change", ScriptedCritic()),
            model=author.model(),
            base=base,
            instruction="Change the checkpoint question in topic 2.",
            section_ids=("learning-topic-2",),
        )

    assert str(raised.value) == GOALS_CHANGE_MESSAGE
    assert "Regenerate goals" in GOALS_CHANGE_MESSAGE


async def test_unknown_section_ids_are_rejected_before_any_model_call(tmp_path):
    base = await _base(tmp_path)
    author = ChangeAuthor()
    with pytest.raises(CanvasChangeRequestError, match="no longer exists"):
        await run_change_job(
            lecture_job(tmp_path / "change", ScriptedCritic()),
            model=author.model(),
            base=base,
            instruction=INSTRUCTION,
            section_ids=("learning-unknown",),
        )
    assert author.calls == []
