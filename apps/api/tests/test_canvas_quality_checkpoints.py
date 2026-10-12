from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.course_canvas_quality import _quality_messages, canvas_quality_response_format
from lecturepilot.course_canvas_quality_checkpoints import checkpoint_contracts
from lecturepilot.course_practice_design_evidence import PracticeSourceAnchor
from practice_design_test_helpers import practice_design_for_canvas
from practice_design_review_test_helpers import source_document


def candidate_with_checkpoint(source, design):
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
    return source.model_copy(update={"sections": [section]})


def test_contract_carries_exact_anchors_and_rubric_but_not_hidden_tasks():
    source = source_document()
    design = practice_design_for_canvas(source)
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
    design = design.model_copy(update={"targets": (target,)})
    contract = checkpoint_contracts(design, candidate_with_checkpoint(source, design))[
        f"practice-{target.id}"
    ]
    evidence = " ".join(contract.evidence.values())
    assert "Later-page distinction." in evidence
    assert "Unlabeled inputs support clustering." in evidence
    assert "[lecture-01.md]" in evidence
    assert all(key.startswith(f"{target.id}:e") for key in contract.evidence)
    assert contract.rubric and contract.task == target.baseline_task
    assert target.independent_exit_task not in evidence
    assert target.delayed_transfer_task not in evidence


def test_single_critic_call_receives_contracts_without_mutating_source():
    source = source_document()
    design = practice_design_for_canvas(source)
    original = source.model_dump_json()
    candidate = candidate_with_checkpoint(source, design)
    contracts = checkpoint_contracts(design, candidate)
    system, user = _quality_messages(source, candidate, contracts)
    assert "APPROVED CHECKPOINT CONTRACTS" in user["content"]
    assert f"CHECKPOINT practice-{design.targets[0].id}" in user["content"]
    assert "design_conflict only when the approved task or rubric itself" in system["content"]
    schema = canvas_quality_response_format(candidate, contracts)["json_schema"]["schema"]
    issue = schema["properties"]["issues"]["items"]["properties"]
    assert issue["decision"]["enum"] == ["repair_section", "design_conflict", "dismiss"]
    assert issue["evidence_ids"]["items"]["enum"] == list(next(iter(contracts.values())).evidence)
    assert source.model_dump_json() == original
