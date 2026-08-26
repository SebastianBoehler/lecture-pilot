from collections.abc import Callable
from pathlib import Path

import pytest

from lecturepilot.course_practice_design_models import (
    PracticeDesign,
    PracticeDesignProposal,
    PracticeDesignUpdate,
)
from lecturepilot.course_practice_design_store import PracticeDesignStore
from lecturepilot.course_practice_design_validation import PracticeDesignValidationError
from lecturepilot.storage_layout import StorageLayout
from practice_design_test_helpers import proposal, target


SRC = "a" * 64
PATHS = ("lecture-01.md",)
Mutation = Callable[[list[dict]], list[dict]]


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda targets: _rename(targets, 0, "id", "renamed-target"), id="target-rename"
        ),
        pytest.param(lambda targets: [targets[1], targets[0]], id="target-reorder"),
        pytest.param(lambda targets: targets[:1], id="target-remove"),
        pytest.param(lambda targets: [*targets, _target_dict("third-target")], id="target-add"),
        pytest.param(
            lambda targets: _rename_nested(targets, "evidence_criteria", 0, "renamed-criterion"),
            id="criterion-rename",
        ),
        pytest.param(
            lambda targets: _reorder_nested(targets, "evidence_criteria"),
            id="criterion-reorder",
        ),
        pytest.param(
            lambda targets: _remove_nested(targets, "evidence_criteria"),
            id="criterion-remove",
        ),
        pytest.param(
            lambda targets: _add_nested(
                targets,
                "evidence_criteria",
                {
                    "id": "extra-criterion",
                    "description": "Checks another reason.",
                    "required": False,
                },
            ),
            id="criterion-add",
        ),
        pytest.param(
            lambda targets: _rename_nested(targets, "misconceptions", 0, "renamed-misconception"),
            id="misconception-rename",
        ),
        pytest.param(
            lambda targets: _reorder_nested(targets, "misconceptions"),
            id="misconception-reorder",
        ),
        pytest.param(
            lambda targets: _remove_nested(targets, "misconceptions"),
            id="misconception-remove",
        ),
        pytest.param(
            lambda targets: _add_nested(
                targets,
                "misconceptions",
                {
                    "id": "extra-misconception",
                    "description": "Uses an unsupported shortcut.",
                    "diagnostic_cue": "The response skips the cited evidence.",
                },
            ),
            id="misconception-add",
        ),
    ],
)
def test_ordinary_update_rejects_identity_skeleton_changes_without_writing(
    tmp_path: Path, mutate: Mutation
) -> None:
    store = PracticeDesignStore(StorageLayout(tmp_path))
    saved = _save_two_target_design(store)
    targets = [item.model_dump(mode="json") for item in saved.targets]
    update = PracticeDesignUpdate(
        source_revision=SRC,
        practice_design_revision=saved.revision,
        lecture_title=saved.lecture_title,
        objective="A permitted content edit that must not mask an identity change.",
        planning_context=saved.planning_context,
        targets=mutate(targets),
    )

    with pytest.raises(PracticeDesignValidationError, match="Stable practice design IDs"):
        store.update(
            course_id="course-01",
            lecture_id="lecture-01",
            current_source_revision=SRC,
            update=update,
            allowed_source_paths=PATHS,
        )

    assert store.read(course_id="course-01", lecture_id="lecture-01") == saved


def _save_two_target_design(store: PracticeDesignStore) -> PracticeDesign:
    proposal_model = proposal()
    first = target(
        evidence_criteria=[
            {"id": "cite-evidence", "description": "Cites the relevant evidence."},
            {"id": "justify-reason", "description": "Justifies the conclusion."},
        ],
        misconceptions=[
            {
                "id": "ignore-evidence",
                "description": "States a conclusion without evidence.",
                "diagnostic_cue": "The response omits a source-grounded reason.",
            },
            {
                "id": "reverse-reasoning",
                "description": "Reverses the evidence relation.",
                "diagnostic_cue": "The stated direction contradicts the source.",
            },
        ],
    )
    second = target(
        id="parallel-conclusion",
        title="Derive a parallel conclusion",
        outcome="Derive a parallel justified conclusion from the given evidence.",
        baseline_task="Derive the parallel conclusion and justify the reasoning.",
        independent_exit_task="Derive another parallel conclusion and justify it.",
        delayed_transfer_task="Derive the parallel conclusion after details change.",
    )
    return store.save_proposal(
        course_id="course-01",
        lecture_id="lecture-01",
        source_revision=SRC,
        proposal=PracticeDesignProposal(
            lecture_title=proposal_model.lecture_title,
            objective=proposal_model.objective,
            planning_context=proposal_model.planning_context,
            targets=(first, second),
        ),
        allowed_source_paths=PATHS,
        expected_design_revision=None,
        expected_design_approval=None,
    )


def _target_dict(target_id: str) -> dict:
    return target(
        id=target_id,
        title="Third target",
        outcome="Derive a third justified conclusion from the given evidence.",
        baseline_task="Derive the third conclusion and justify the reasoning.",
        independent_exit_task="Derive a new third conclusion and justify it.",
        delayed_transfer_task="Derive the third conclusion after details change.",
    ).model_dump(mode="json")


def _rename(targets: list[dict], index: int, key: str, value: str) -> list[dict]:
    changed = [dict(item) for item in targets]
    changed[index][key] = value
    return changed


def _rename_nested(targets: list[dict], field: str, index: int, value: str) -> list[dict]:
    changed = [dict(item) for item in targets]
    nested = [dict(item) for item in changed[0][field]]
    nested[index]["id"] = value
    changed[0][field] = nested
    return changed


def _reorder_nested(targets: list[dict], field: str) -> list[dict]:
    changed = [dict(item) for item in targets]
    changed[0][field] = list(reversed(changed[0][field]))
    return changed


def _remove_nested(targets: list[dict], field: str) -> list[dict]:
    changed = [dict(item) for item in targets]
    changed[0][field] = changed[0][field][:-1]
    return changed


def _add_nested(targets: list[dict], field: str, item: dict) -> list[dict]:
    changed = [dict(value) for value in targets]
    changed[0][field] = [*changed[0][field], item]
    return changed
