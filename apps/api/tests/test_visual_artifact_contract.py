import pytest
from pydantic import ValidationError

from lecturepilot.canvas_component_catalog import component_block_from_payload, component_spec_issue
from lecturepilot.canvas_models import CanvasBlock, CanvasComponentData
from lecturepilot.component_response_schema import component_data_schema


def test_component_catalog_accepts_composable_visual_artifact() -> None:
    visual = _visual_block(
        {
            "visual_layout": "flow",
            "visual_nodes": [
                {"id": "prior", "label": "Prior", "detail": "Initial belief"},
                {"id": "evidence", "label": "Evidence", "detail": "Observed data"},
                {"id": "posterior", "label": "Posterior", "detail": "Updated belief"},
            ],
            "visual_edges": [
                {"from_id": "prior", "to_id": "evidence", "label": "combine"},
                {"from_id": "evidence", "to_id": "posterior", "label": "update"},
            ],
            "visual_annotations": [
                {"label": "The likelihood controls the update.", "target_id": "evidence"}
            ],
        }
    )

    assert component_spec_issue(visual) is None


def test_component_catalog_rejects_visual_edges_with_unknown_nodes() -> None:
    visual = _visual_block(
        {
            "visual_layout": "flow",
            "visual_nodes": [
                {"id": "start", "label": "Start", "detail": "Known node"},
                {"id": "finish", "label": "Finish", "detail": "Known node"},
            ],
            "visual_edges": [
                {"from_id": "missing", "to_id": "finish", "label": None},
            ],
        }
    )

    assert component_spec_issue(visual) == "references an unknown visual node."


def test_visual_artifact_models_reject_unbounded_or_non_finite_data() -> None:
    with pytest.raises(ValidationError):
        CanvasComponentData.model_validate(
            {
                "visual_layout": "grid",
                "visual_nodes": [
                    {"id": f"node-{index}", "label": "Node", "detail": "Bounded"}
                    for index in range(13)
                ],
            }
        )

    with pytest.raises(ValidationError):
        CanvasComponentData.model_validate(
            {
                "visual_layout": "plot",
                "x_label": "Step",
                "y_label": "Loss",
                "visual_series": [
                    {
                        "label": "Training",
                        "mark": "line",
                        "points": [
                            {"label": "Start", "x": 0, "y": float("nan"), "series": None},
                            {"label": "End", "x": 1, "y": 0.1, "series": None},
                        ],
                    }
                ],
            }
        )


def test_component_catalog_rejects_incomplete_visual_plot() -> None:
    visual = _visual_block(
        {
            "visual_layout": "plot",
            "x_label": "Step",
            "y_label": "Loss",
            "visual_series": [
                {
                    "label": "Training",
                    "mark": "line",
                    "points": [
                        {"label": "Start", "x": 0, "y": 1, "series": None},
                    ],
                }
            ],
        }
    )

    assert component_spec_issue(visual) == (
        "needs at least two finite points in every visual series."
    )


def test_component_response_schema_exposes_visual_grammar() -> None:
    schema = component_data_schema()

    assert {"flow", "timeline", "grid", "plot"}.issubset(
        schema["properties"]["visual_layout"]["enum"]
    )
    assert schema["properties"]["visual_nodes"]["maxItems"] == 12
    assert schema["properties"]["visual_edges"]["maxItems"] == 16
    assert schema["properties"]["visual_series"]["maxItems"] == 6
    assert {
        "visual_layout",
        "visual_nodes",
        "visual_edges",
        "visual_series",
        "visual_annotations",
    }.issubset(schema["required"])


def test_generated_component_ref_is_derived_from_backend_block_id() -> None:
    payload = {
        "component_id": "reused-provider-id",
        "component_ref": "reused-provider-path.yaml",
        "component_type": "visual_artifact",
        "component_version": 1,
        "component_data": {
            "visual_layout": "grid",
            "visual_nodes": [
                {"id": "a", "label": "A", "detail": "First"},
                {"id": "b", "label": "B", "detail": "Second"},
            ],
        },
    }
    block = component_block_from_payload(payload, "learning-topic-component-1")
    unsafe = component_block_from_payload(payload, "../other-topic")

    assert block.component_ref == "learning-topic-component-1.yaml"
    assert unsafe.component_ref == "other-topic.yaml"


def _visual_block(data: dict) -> CanvasBlock:
    return CanvasBlock(
        id="visual",
        type="component",
        component_type="visual_artifact",
        component_version=1,
        component_data=CanvasComponentData.model_validate(data),
    )
