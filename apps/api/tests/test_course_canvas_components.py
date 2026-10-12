from lecturepilot.canvas_component_catalog import component_spec_issue
from lecturepilot.canvas_models import (
    CanvasBlock,
    CanvasComponentData,
    CanvasComponentFrame,
    CanvasComponentPoint,
)


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
