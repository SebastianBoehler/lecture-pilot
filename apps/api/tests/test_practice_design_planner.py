from lecturepilot.canvas.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from practice_design_test_helpers import proposal, target
from lecturepilot.learning_design.practice_evidence_catalogue import evidence_catalogue


SOURCE_REVISION = "a" * 64


def _source() -> CanvasDocument:
    return CanvasDocument(
        id="c-l",
        course_id="c",
        lecture_id="l",
        title="Bayes rule",
        source_kind="markdown",
        source_ref="lecture.md",
        workspace_path="source.json",
        sections=[
            CanvasSection(
                id="bayes",
                title="Bayes rule",
                source_ref="lecture.md",
                blocks=[CanvasBlock(id="evidence", type="paragraph", text="Posterior evidence.")],
            )
        ],
    )


def test_teaching_prompt_states_the_contract_and_exact_authoritative_source_paths() -> None:
    from lecturepilot.learning_design.course_practice_design_prompt import practice_design_messages
    from lecturepilot.learning_design.course_practice_design_review_prompt import (
        practice_design_review_messages,
    )

    source = _source().model_copy(
        update={
            "sections": [
                *_source().sections,
                _source().sections[0].model_copy(update={"id": "x", "source_ref": "unrouted.md"}),
            ]
        }
    )
    catalogue = evidence_catalogue(source, ("lecture.md",))
    messages = practice_design_messages(
        source,
        source_revision=SOURCE_REVISION,
        allowed_source_paths=("lecture.md",),
        catalogue=catalogue,
    )
    request = {"instructions": messages[0]["content"], "messages": messages[1:]}
    instruction = request["instructions"]
    assert "minimum set of distinct capabilities supported by the source" in instruction
    assert "3 to 6 targets" not in instruction
    assert "Diagnostic attempt" in instruction
    assert "Independent exit" in instruction
    assert "Delayed transfer" in instruction
    assert "Atomic evidence criteria" in instruction
    assert "prompt asks the learner to inspect or plan" in instruction
    assert "worked_step gives one justified step" in instruction
    assert "not a claim that this interval is scientifically optimal" in instruction
    assert "solve it from its stated givens" in instruction
    assert "Contradictory givens make a task unassessable" in instruction
    assert "lecture.md" in str(request["messages"])
    assert "unrouted.md" not in str(request["messages"])
    review = practice_design_review_messages(
        source,
        proposal().model_copy(
            update={
                "targets": (
                    target(source_refs=("lecture.md",), source_excerpt="Posterior evidence."),
                )
            }
        ),
        source_revision=SOURCE_REVISION,
        allowed_source_paths=("lecture.md",),
        catalogue=catalogue,
    )
    assert "SOURCE EVIDENCE" in review[1]["content"]
    assert "solve it from its stated givens" in review[0]["content"]


def test_response_schema_describes_the_assessment_and_scaffold_contract() -> None:
    from lecturepilot.learning_design.course_practice_design_prompt import (
        practice_design_response_format,
    )

    schema = practice_design_response_format(evidence_catalogue(_source(), ("lecture.md",)))[
        "json_schema"
    ]["schema"]
    target_schema = schema["$defs"]["PracticeTarget"]["properties"]
    criterion_schema = schema["$defs"]["PracticeEvidenceCriterion"]["properties"]
    misconception_schema = schema["$defs"]["PracticeMisconception"]["properties"]
    hint_schema = schema["$defs"]["PracticeHint"]["properties"]

    assert "diagnostic attempt" in target_schema["baseline_task"]["description"].lower()
    assert "unaided" in target_schema["independent_exit_task"]["description"].lower()
    assert "changed-form" in target_schema["delayed_transfer_task"]["description"].lower()
    assert "atomic" in criterion_schema["description"]["description"].lower()
    assert "boundary" in misconception_schema["description"]["description"].lower()
    hint_description = hint_schema["level"]["description"]
    for level in ("prompt", "cue", "faded_example", "worked_step"):
        assert level in hint_description
