import pytest
from pydantic import ValidationError

from lecturepilot.agent_tool_loop import _with_tool_instruction
from lecturepilot.canvas_models import (
    CanvasComponentData,
    CanvasComponentFrame,
)
from lecturepilot.provider_canvas_models import ProviderCanvasBlock
from lecturepilot.raster_request_intent import is_explicit_raster_request


def test_tool_instruction_only_requires_image_tool_for_raster_requests() -> None:
    content = _with_tool_instruction([{"role": "system", "content": "Tutor."}], "tutor")[0][
        "content"
    ]

    assert "prefer a trusted component" in content
    assert "visual_artifact" in content
    assert "Call generate_image before your final answer." not in content
    assert "Do not call generate_image as a fallback" in content


@pytest.mark.parametrize(
    "prompt",
    [
        "Create a raster image comparing the two mechanisms.",
        "Export the explanation as a PNG image.",
        "Add an image of the decision boundary.",
        "Can you turn this into a PNG?",
        "Please give me an image of the mechanism.",
        "Create a real infographic image for Bayes.",
        "Create a raster of the mechanism.",
        "Draw pixel art of the concept.",
        "Add an image asset to the learner section.",
        "Return a JPEG image.",
        "Erstelle ein Bild von der Entscheidungsgrenze.",
        "Exportiere die Erklärung als PNG.",
    ],
)
def test_explicit_raster_output_requests_are_detected(prompt: str) -> None:
    assert is_explicit_raster_request(prompt)


@pytest.mark.parametrize(
    "prompt",
    [
        "Create a diagram comparing the two mechanisms.",
        "Erstelle ein Diagramm, das beide Mechanismen vergleicht.",
        "Generate an infographic showing the update.",
        "Create a chart comparing image classification models.",
        "Plot image segmentation scores by model.",
        "Explain the JPEG compression pipeline as a diagram.",
        "Compare photo quality metrics in a plot.",
        "Generate a chart of PNG compression ratios.",
        "Create a lesson about JPEG compression as a diagram.",
        "Use photo quality metrics in a plot.",
        "Show photo quality as a table.",
        "Visualisiere Ausbildungswege als Tabelle.",
    ],
)
def test_visual_topic_words_do_not_force_a_raster(prompt: str) -> None:
    assert not is_explicit_raster_request(prompt)


def test_provider_parses_declarative_visual_artifact() -> None:
    parsed = ProviderCanvasBlock.model_validate(_provider_visual_payload())

    assert parsed.component_type == "visual_artifact"
    assert parsed.to_domain().component_data.visual_layout == "flow"


def test_provider_rejects_visual_references_to_unknown_nodes() -> None:
    payload = _provider_visual_payload()
    payload["component_data"]["visual_edges"][0]["from_id"] = "missing"

    with pytest.raises(ValidationError, match="unknown visual node"):
        ProviderCanvasBlock.model_validate(payload)


def test_provider_rejects_unknown_visual_artifact_version() -> None:
    payload = _provider_visual_payload()
    payload["component_version"] = 2

    with pytest.raises(ValidationError, match="unsupported visual_artifact component_version"):
        ProviderCanvasBlock.model_validate(payload)


def test_component_models_reject_non_finite_numbers() -> None:
    with pytest.raises(ValidationError):
        CanvasComponentData(
            labels=["A", "B"],
            frames=[
                CanvasComponentFrame(
                    label="Invalid",
                    values=[float("nan"), 1],
                    explanation="The value is not finite.",
                )
            ],
        )


def _provider_visual_payload() -> dict:
    return {
        "id": "bayes-flow",
        "type": "component",
        "text": "Follow the information flow.",
        "items": [],
        "asset_path": None,
        "asset_url": None,
        "caption": "Bayesian update",
        "answer_index": None,
        "component_id": "bayes-flow",
        "component_type": "visual_artifact",
        "component_ref": None,
        "component_version": 1,
        "option_ids": [],
        "component_data": {
            "chart_type": None,
            "control_type": None,
            "x_label": None,
            "y_label": None,
            "control_label": None,
            "labels": [],
            "row_labels": [],
            "frames": [],
            "steps": [],
            "visual_layout": "flow",
            "visual_nodes": [
                {"id": "prior", "label": "Prior", "detail": "Initial belief"},
                {"id": "posterior", "label": "Posterior", "detail": "Updated belief"},
            ],
            "visual_edges": [
                {"from_id": "prior", "to_id": "posterior", "label": "evidence"},
            ],
            "visual_series": [],
            "visual_annotations": [],
        },
    }
