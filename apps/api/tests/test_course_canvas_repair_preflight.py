import json
import sys
from types import SimpleNamespace

import pytest

from canvas_workspace_fixtures import published_course_canvas
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.course_canvas_assessment_normalizer import normalize_section_assessments
from lecturepilot.course_canvas_math import normalize_generated_math, validate_section_math
from lecturepilot.course_canvas_planner import LiteLLMCoursePlanClient
from lecturepilot.course_canvas_repair_preflight import (
    normalize_repair_candidate,
    repair_failure_constraint,
)
from lecturepilot.providers import ProviderRegistry
from test_course_canvas_section_repair import _planner, _repair_payload
from test_course_canvas_math import _section_with_math
from test_course_canvas_targeted_repair import _invalid_candidate


def test_generated_math_normalization_removes_stray_display_delimiters() -> None:
    formula = r"\begin{aligned}a &= b \\ \[c &= d\end{aligned}"

    normalized = normalize_generated_math(formula)

    assert normalized == r"\begin{aligned}a &= b \\ c &= d\end{aligned}"
    validate_section_math(_section_with_math(normalized))


def test_component_repair_constraint_requires_a_complete_schema_payload() -> None:
    constraint = repair_failure_constraint(
        "Component block chart-1 needs chart_type and at least one frame."
    )

    assert "component_data" in constraint
    assert "chart_type" in constraint
    assert "frame" in constraint


def test_choice_component_repair_constraint_requires_explicit_answers() -> None:
    constraint = repair_failure_constraint(
        "Component block choice-1 needs at least two options and one explicit correct answer."
    )

    assert "at least two options" in constraint
    assert "correct answer" in constraint


def test_unsupported_factual_claim_uses_grounding_repair_not_math_repair() -> None:
    constraint = repair_failure_constraint(
        "The supplied source evidence does not establish the claimed four-way evaluation."
    )

    assert "remove" in constraint.casefold()
    assert "claim" in constraint.casefold()
    assert "portable KaTeX commands" not in constraint


def test_assessment_only_section_builds_checkpoint_from_selected_grounded_answer() -> None:
    section = CanvasSection(
        id="labels",
        title="Labels",
        source_ref="nested/course/material.pdf page 2",
        blocks=[
            CanvasBlock(
                id="labels-choice",
                type="component",
                text="Which labels are shown?",
                items=[
                    "Hyperparameters; avg acc; retrain with all training data",
                    "Candidate model; score; selected fold",
                ],
                answer_index=0,
                component_id="labels-choice",
                component_type="single_choice_quiz",
                component_ref="components/labels-choice.yaml",
                component_version=1,
                option_ids=["a", "b"],
            )
        ],
    )

    normalized = normalize_section_assessments(section, output_language="en")

    checkpoint = normalized.blocks[-1]
    assert checkpoint.type == "checkpoint"
    assert "Hyperparameters; avg acc" in (checkpoint.text or "")
    assert "List the explicitly named elements" in (checkpoint.text or "")
    assert "relationship" not in (checkpoint.text or "")


def test_duplicate_choice_options_become_a_grounded_checkpoint_without_model_repair() -> None:
    candidate = published_course_canvas("duplicate-choice", "lecture-01")
    section = candidate.sections[0]
    section = section.model_copy(
        update={
            "blocks": [
                section.blocks[0].model_copy(
                    update={"text": "A grounded instructional statement with enough detail."}
                )
            ]
        }
    )
    duplicate = CanvasBlock(
        id="duplicate-choice",
        type="component",
        text="Which statement is correct?",
        items=["A visibly truncated answer...", "A visibly truncated answer..."],
        answer_index=0,
        component_id="duplicate-choice",
        component_type="single_choice_quiz",
        component_ref="components/duplicate-choice.yaml",
        component_version=1,
        option_ids=["a", "b"],
    )
    candidate = candidate.model_copy(
        update={
            "sections": [
                section.model_copy(update={"blocks": [*section.blocks, duplicate]}),
                *candidate.sections[1:],
            ]
        }
    )

    normalized = normalize_repair_candidate(
        candidate,
        section.id,
        duplicate.id,
        "Both answer options are identical and visibly truncated.",
    )

    target = normalized.sections[0].blocks[-1]
    assert target.type == "checkpoint"
    assert "grounded instructional statement" in (target.text or "")
    assert target.items == []
    assert target.component_type is None


async def test_course_plan_client_applies_repair_temperature(monkeypatch) -> None:
    calls = []
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        choice = SimpleNamespace(
            finish_reason="stop",
            message=SimpleNamespace(content=json.dumps({"title": "T", "sections": []})),
        )
        return SimpleNamespace(choices=[choice])

    monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(acompletion=fake_completion))

    await LiteLLMCoursePlanClient().complete_plan(
        settings=ProviderRegistry.from_env("gemini/test-model").require_ready([]),
        messages=[{"role": "user", "content": "Repair"}],
        temperature=0.3,
    )

    assert calls[0]["temperature"] == 0.3


async def test_section_repair_normalizes_redundant_math_without_calling_the_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner, model = _planner(monkeypatch, [])
    source = published_course_canvas("targeted-repair", "lecture-01")
    candidate = _invalid_candidate(source)
    section = candidate.sections[0]
    target = section.blocks[1].model_copy(update={"text": r"w^\prime \[x"})
    candidate = candidate.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={"blocks": [section.blocks[0], target, *section.blocks[2:]]}
                ),
                *candidate.sections[1:],
            ]
        }
    )

    repaired = await planner.repair_section(
        source,
        candidate,
        section_id=section.id,
        block_id=target.id,
        failure_context="Math block contains display delimiters.",
    )

    repaired_target = next(block for block in repaired.sections[0].blocks if block.id == target.id)
    assert repaired_target.text == r"w^\prime x"
    assert model.messages == []


async def test_section_repair_normalizes_source_dependent_checkpoint_without_model_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner, model = _planner(monkeypatch, [])
    source = published_course_canvas("targeted-repair", "lecture-01")
    candidate = _invalid_candidate(source)
    section = candidate.sections[0]
    valid_math = section.blocks[1].model_copy(update={"text": r"w^\top x"})
    target = section.blocks[4].model_copy(
        update={"text": "This slide summarizes the optimization workflow."}
    )
    candidate = candidate.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={
                        "blocks": [
                            section.blocks[0],
                            valid_math,
                            *section.blocks[2:4],
                            target,
                            *section.blocks[5:],
                        ]
                    }
                ),
                *candidate.sections[1:],
            ]
        }
    )

    repaired = await planner.repair_section(
        source,
        candidate,
        section_id=section.id,
        block_id=target.id,
        failure_context="Checkpoint must be understandable without a slide reference.",
    )

    repaired_target = next(block for block in repaired.sections[0].blocks if block.id == target.id)
    assert "slide" not in repaired_target.text.casefold()
    assert "this statement" in repaired_target.text.casefold()
    assert model.messages == []


async def test_section_repair_converts_incomplete_choice_component_without_model_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner, model = _planner(monkeypatch, [])
    source = published_course_canvas("targeted-repair", "lecture-01")
    candidate = _invalid_candidate(source)
    section = candidate.sections[0]
    valid_math = section.blocks[1].model_copy(update={"text": r"w^\top x"})
    target = section.blocks[4].model_copy(
        update={
            "id": "optimization-choice",
            "type": "component",
            "text": "Explain how the transpose aligns the vector dimensions.",
            "items": [],
            "answer_index": None,
            "component_id": "optimization-choice",
            "component_type": "single_choice_quiz",
            "component_ref": "components/optimization-choice.yaml",
            "component_version": 1,
            "option_ids": [],
        }
    )
    candidate = candidate.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={
                        "blocks": [
                            section.blocks[0],
                            valid_math,
                            *section.blocks[2:4],
                            target,
                            *section.blocks[5:],
                        ]
                    }
                ),
                *candidate.sections[1:],
            ]
        }
    )

    repaired = await planner.repair_section(
        source,
        candidate,
        section_id=section.id,
        block_id=target.id,
        failure_context=(
            "Component block optimization-choice needs at least two options and one explicit "
            "correct answer."
        ),
    )

    repaired_target = next(block for block in repaired.sections[0].blocks if block.id == target.id)
    assert repaired_target.type == "checkpoint"
    assert repaired_target.text == target.text
    assert repaired_target.component_id is None
    assert repaired_target.component_type is None
    assert model.messages == []


async def test_section_repair_rewrites_unsupported_relationship_as_retrieval_without_model_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner, model = _planner(monkeypatch, [])
    source = published_course_canvas("targeted-repair", "lecture-01")
    candidate = _invalid_candidate(source)
    section = candidate.sections[0]
    valid_math = section.blocks[1].model_copy(update={"text": r"w^\top x"})
    choice = CanvasBlock(
        id="workflow-labels",
        type="component",
        text="Which labels are shown?",
        items=[
            "Hyperparameters; avg acc; acc1 acc2 acc3 acc4; retrain with all training data",
            "Training; evaluation; deployment",
        ],
        answer_index=0,
        component_id="workflow-labels",
        component_type="single_choice_quiz",
        component_ref="components/workflow-labels.yaml",
        component_version=1,
        option_ids=["a", "b"],
    )
    target = section.blocks[4].model_copy(
        update={"text": "Explain the relationship among acc1, acc2, acc3, and retraining."}
    )
    candidate = candidate.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={
                        "blocks": [
                            section.blocks[0],
                            valid_math,
                            *section.blocks[2:4],
                            choice,
                            target,
                            *section.blocks[5:],
                        ]
                    }
                ),
                *candidate.sections[1:],
            ]
        }
    )

    repaired = await planner.repair_section(
        source,
        candidate,
        section_id=section.id,
        block_id=target.id,
        failure_context=(
            "Canvas quality review failed: the source only displays the labels and does not "
            "state or explain a relationship among them; the checkpoint asks for unsupported "
            "interpretation."
        ),
    )

    repaired_target = next(block for block in repaired.sections[0].blocks if block.id == target.id)
    assert "List the explicitly named elements" in (repaired_target.text or "")
    assert "relationship" not in (repaired_target.text or "")
    assert model.messages == []


async def test_section_repair_downgrades_multi_correct_choice_without_model_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner, model = _planner(monkeypatch, [])
    source = published_course_canvas("targeted-repair", "lecture-01")
    candidate = _invalid_candidate(source)
    section = candidate.sections[0]
    valid_math = section.blocks[1].model_copy(update={"text": r"w^\top x"})
    target = section.blocks[5]
    candidate = candidate.model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={"blocks": [section.blocks[0], valid_math, *section.blocks[2:]]}
                ),
                *candidate.sections[1:],
            ]
        }
    )

    repaired = await planner.repair_section(
        source,
        candidate,
        section_id=section.id,
        block_id=target.id,
        failure_context=(
            "Canvas quality review failed: the selected answer is supported, but the second "
            "option is also supported and the answer is not uniquely correct."
        ),
    )

    repaired_target = next(block for block in repaired.sections[0].blocks if block.id == target.id)
    assert repaired_target.type == "checkpoint"
    assert "List the explicitly named elements" in (repaired_target.text or "")
    assert model.messages == []


async def test_block_repair_accepts_the_evidence_supported_patch_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    replacement = _repair_payload(
        [{"type": "paragraph", "text": f"Source-supported detail {index}."} for index in range(4)]
    )
    planner, _model = _planner(monkeypatch, [replacement])
    source = published_course_canvas("targeted-repair", "lecture-01")

    repaired = await planner.repair_section(
        source,
        _invalid_candidate(source),
        section_id="learning-optimization",
        block_id="optimization-math",
        failure_context="Repair only the failed formula.",
    )

    assert len(repaired.sections[0].blocks) == 9
