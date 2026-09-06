import json

import pytest

from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.course_practice_design_models import PracticeDesignProposal
from practice_design_test_helpers import proposal
from test_practice_design_planner import _source


def test_catalogue_maps_provider_ids_to_exact_routed_evidence_without_mutation():
    from lecturepilot.practice_evidence_catalogue import evidence_catalogue, expand_evidence_ids

    catalogue = evidence_catalogue(_source(), ("lecture.md",))
    assert catalogue == {"e0": {"source_path": "lecture.md", "excerpt": "Posterior evidence."}}
    payload = proposal().model_dump(mode="json")

    def compact(value):
        if isinstance(value, dict):
            if "source_path" in value:
                return "e0"
            return {key: compact(item) for key, item in value.items() if key != "source_refs"}
        if isinstance(value, list):
            return [compact(item) for item in value]
        return value

    wire = compact(payload)
    expanded = expand_evidence_ids(wire, catalogue, derive_source_refs=True)
    validated = PracticeDesignProposal.model_validate(expanded)
    assert validated.targets[0].source_refs == ("lecture.md",)
    assert validated.targets[0].outcome_anchor.excerpt == "Posterior evidence."
    assert wire["targets"][0]["outcome_anchor"] == "e0"
    assert validated.targets[0].baseline_task == payload["targets"][0]["baseline_task"]


@pytest.mark.parametrize("anchor", ["unknown", {"source_path": "lecture.md", "excerpt": "Fake"}])
def test_unknown_or_inline_anchor_cannot_bypass_the_catalogue(anchor):
    from lecturepilot.practice_evidence_catalogue import expand_evidence_ids

    with pytest.raises(ValueError, match="evidence"):
        expand_evidence_ids({"outcome_anchor": anchor}, {})


@pytest.mark.parametrize(
    "payload",
    [
        {"supporting_anchors": None},
        {"supporting_anchors": "e0"},
        {"targets": None},
        {"targets": ["invalid"]},
        {"targets": [{"evidence_criteria": [None]}]},
    ],
)
def test_malformed_provider_collections_fail_with_validation_error(payload):
    from lecturepilot.course_practice_design_validation import PracticeDesignValidationError
    from lecturepilot.practice_evidence_catalogue import expand_evidence_ids

    with pytest.raises(PracticeDesignValidationError):
        expand_evidence_ids(payload, {}, derive_source_refs=True)


def test_catalogue_excludes_unrouted_sources_and_bounds_packet_without_front_loading():
    from lecturepilot.practice_evidence_catalogue import evidence_catalogue

    source = _source()
    first = source.sections[0]
    sections = [
        first.model_copy(
            update={
                "id": f"s{i}",
                "blocks": [
                    CanvasBlock(
                        id=f"b{i}-{j}",
                        type="paragraph",
                        text=f"Section {i} block {j}: " + "x" * 1580,
                    )
                    for j in range(50)
                ],
            }
        )
        for i in range(8)
    ]
    sections.append(first.model_copy(update={"source_ref": "private-other.md"}))
    catalogue = evidence_catalogue(
        source.model_copy(update={"sections": sections}), ("lecture.md",)
    )
    assert len(json.dumps(catalogue, ensure_ascii=False)) <= 80_000
    assert len(catalogue) <= 512
    assert all(anchor["source_path"] == "lecture.md" for anchor in catalogue.values())
    assert {anchor["excerpt"].split()[1] for anchor in catalogue.values()} == set(
        map(str, range(8))
    )
