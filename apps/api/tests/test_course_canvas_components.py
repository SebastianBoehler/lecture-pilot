from lecturepilot.canvas_component_catalog import (
    component_spec_issue,
    normalize_document_component_identities,
)
from lecturepilot.canvas_models import (
    CanvasBlock,
    CanvasComponentData,
    CanvasComponentFrame,
    CanvasComponentPoint,
    CanvasDocument,
    CanvasSection,
)
from lecturepilot.component_response_schema import component_data_schema
from lecturepilot.course_canvas_section_planner import plan_sections_individually
from lecturepilot.models import ProviderSettings


async def test_section_planner_creates_catalogued_interactive_chart() -> None:
    planned = await plan_sections_individually(
        model_client=_CatalogAwarePlanClient(),
        settings=ProviderSettings(
            provider="test",
            model="test/model",
            api_key_env="TEST_API_KEY",
            capabilities=set(),
        ),
        source_document=_source_document(),
    )

    component = planned.sections[0].blocks[0]
    assert component.type == "component"
    assert component.component_id == component.id
    assert component.component_ref == f"{component.id}.yaml"
    assert component.component_type == "interactive_chart"
    assert component.component_data is not None
    assert component.component_data.labels == ["Prior", "Posterior"]
    assert component.component_data.frames[1].values == [0.4, 0.6]


def test_existing_component_ids_are_normalized_from_stable_block_ids() -> None:
    document = _source_document().model_copy(
        update={
            "sections": [
                section.model_copy(
                    update={
                        "blocks": [
                            CanvasBlock(
                                id=f"choice-{index}",
                                type="component",
                                text="Choose one.",
                                items=["A", "B"],
                                answer_index=0,
                                component_id="duplicate-model-id",
                                component_type="single_choice_quiz",
                                component_ref="duplicate-model-id.yaml",
                                component_version=1,
                                option_ids=["a", "b"],
                            )
                        ]
                    }
                )
                for index, section in enumerate(_source_document().sections, start=1)
            ]
        }
    )

    normalized = normalize_document_component_identities(document)
    component = normalized.sections[0].blocks[0]

    assert component.component_id == component.id == "choice-1"
    assert component.component_ref == "choice-1.yaml"


def test_component_catalog_accepts_scatter_and_heatmap_data() -> None:
    scatter = CanvasBlock(
        id="class-clusters",
        type="component",
        component_type="interactive_chart",
        component_data=CanvasComponentData(
            chart_type="scatter",
            x_label="Feature one",
            y_label="Feature two",
            frames=[
                CanvasComponentFrame(
                    label="Observed samples",
                    points=[
                        CanvasComponentPoint(
                            label="Sample A",
                            x=1,
                            y=2,
                            series="Class A",
                        ),
                        CanvasComponentPoint(
                            label="Sample B",
                            x=3,
                            y=4,
                            series="Class B",
                        ),
                    ],
                    explanation="The samples form two visible groups.",
                )
            ],
        ),
    )
    heatmap = CanvasBlock(
        id="prediction-errors",
        type="component",
        component_type="interactive_chart",
        component_data=CanvasComponentData(
            chart_type="heatmap",
            x_label="Predicted class",
            y_label="Actual class",
            labels=["Predicted A", "Predicted B"],
            row_labels=["Actual A", "Actual B"],
            frames=[
                CanvasComponentFrame(
                    label="Validation set",
                    matrix=[[8, 2], [1, 9]],
                    explanation="Most predictions lie on the diagonal.",
                )
            ],
        ),
    )

    assert component_spec_issue(scatter) is None
    assert component_spec_issue(heatmap) is None


def test_component_catalog_accepts_simultaneous_mechanism_comparison() -> None:
    comparison = CanvasBlock(
        id="constraint-handling",
        type="component",
        component_type="mechanism_comparison",
        component_data=CanvasComponentData(
            chart_type="line",
            x_label="Parameter index",
            y_label="Normalized value",
            labels=["Hard power", "Soft power", "Detector"],
            frames=[
                CanvasComponentFrame(
                    label="Sigmoid movement",
                    values=[100, 90, 85],
                    points=[
                        CanvasComponentPoint(label="Start", x=0, y=0.95),
                        CanvasComponentPoint(label="Middle", x=1, y=0.05),
                    ],
                    explanation="Soft bounds preserve collective feasibility.",
                ),
                CanvasComponentFrame(
                    label="Direct projection",
                    values=[117, 104, 104],
                    points=[
                        CanvasComponentPoint(label="Start", x=0, y=1),
                        CanvasComponentPoint(label="Middle", x=1, y=0),
                    ],
                    explanation="Independent clipping violates a shared constraint.",
                ),
            ],
        ),
    )

    assert component_spec_issue(comparison) is None


def test_component_catalog_rejects_single_mechanism_comparison() -> None:
    comparison = CanvasBlock(
        id="one-mechanism",
        type="component",
        component_type="mechanism_comparison",
        component_data=CanvasComponentData(
            chart_type="line",
            x_label="Input",
            y_label="Output",
            labels=["Constraint A", "Constraint B"],
            frames=[
                CanvasComponentFrame(
                    label="Only approach",
                    values=[1, 2],
                    explanation="There is nothing to compare this with.",
                )
            ],
        ),
    )

    assert component_spec_issue(comparison) == "needs two to four mechanism frames."


def test_component_response_schema_exposes_new_chart_shapes() -> None:
    schema = component_data_schema()
    chart_types = schema["properties"]["chart_type"]["enum"]
    control_types = schema["properties"]["control_type"]["enum"]
    frame_properties = schema["properties"]["frames"]["items"]["properties"]

    assert {"bar", "line", "scatter", "heatmap"}.issubset(chart_types)
    assert {"buttons", "slider"}.issubset(control_types)
    assert "control_type" in schema["required"]
    assert "row_labels" in schema["required"]
    assert {"points", "matrix"}.issubset(frame_properties)


def test_component_catalog_rejects_malformed_new_chart_shapes() -> None:
    scatter = CanvasBlock(
        id="thin-scatter",
        type="component",
        component_type="interactive_chart",
        component_data=CanvasComponentData(
            chart_type="scatter",
            x_label="X",
            y_label="Y",
            frames=[
                CanvasComponentFrame(
                    label="Only sample",
                    points=[CanvasComponentPoint(label="A", x=1, y=2)],
                    explanation="One point is not a useful scatter plot.",
                )
            ],
        ),
    )
    heatmap = CanvasBlock(
        id="ragged-heatmap",
        type="component",
        component_type="interactive_chart",
        component_data=CanvasComponentData(
            chart_type="heatmap",
            labels=["A", "B"],
            row_labels=["A", "B"],
            frames=[
                CanvasComponentFrame(
                    label="Ragged",
                    matrix=[[1, 2], [3]],
                    explanation="The second row is incomplete.",
                )
            ],
        ),
    )

    assert component_spec_issue(scatter) == (
        "needs at least two labeled points in every scatter frame."
    )
    assert component_spec_issue(heatmap) == (
        "needs a rectangular matrix matching row_labels and labels in every frame."
    )


class _CatalogAwarePlanClient:
    async def complete_plan(self, *, settings, messages):
        instruction = messages[0]["content"]
        if not all(term in instruction for term in ("interactive_chart", "scatter", "heatmap")):
            return {
                "title": "Bayesian update",
                "blocks": [
                    {"type": "paragraph", "text": "No component catalogue received."},
                    {
                        "type": "checkpoint",
                        "text": "Explain how evidence changes the posterior probability.",
                    },
                ],
            }
        return {
            "title": "Bayesian update",
            "blocks": [
                {
                    "type": "component",
                    "component_id": "bayes-update-chart",
                    "component_type": "interactive_chart",
                    "component_version": 1,
                    "caption": "Prior and posterior",
                    "text": "Move the evidence-strength control and compare the probabilities.",
                    "component_data": {
                        "chart_type": "bar",
                        "x_label": "Belief",
                        "y_label": "Probability",
                        "control_label": "Evidence strength",
                        "labels": ["Prior", "Posterior"],
                        "frames": [
                            {
                                "label": "Weak",
                                "values": [0.5, 0.5],
                                "explanation": "Weak evidence leaves the belief unchanged.",
                            },
                            {
                                "label": "Strong",
                                "values": [0.4, 0.6],
                                "explanation": "Strong evidence shifts probability to the class.",
                            },
                        ],
                        "steps": [],
                    },
                },
                {
                    "type": "checkpoint",
                    "text": "Explain how stronger evidence changes the posterior probability.",
                },
            ],
        }


def _source_document() -> CanvasDocument:
    return CanvasDocument(
        id="course-lecture",
        course_id="course",
        lecture_id="lecture",
        title="Lecture",
        source_kind="latex",
        source_ref="Lecture.tex",
        workspace_path="canvas/index.md",
        sections=[
            CanvasSection(
                id="source-topic",
                title="Bayesian update",
                source_ref="frame 1",
                blocks=[
                    CanvasBlock(
                        id="source-paragraph",
                        type="paragraph",
                        text="Evidence changes the posterior probability.",
                    )
                ],
            )
        ],
    )
