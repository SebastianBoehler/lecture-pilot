from pathlib import Path

from lecturepilot.canvas_markdown import read_document_source, write_document_source
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection


def test_canvas_markdown_roundtrips_scatter_and_heatmap_shapes(tmp_path: Path) -> None:
    scatter = CanvasBlock(
        id="class-clusters",
        type="component",
        component_id="class-clusters",
        component_type="interactive_chart",
        component_ref="class-clusters.yaml",
        caption="Class clusters",
        component_data={
            "chart_type": "scatter",
            "x_label": "Feature one",
            "y_label": "Feature two",
            "control_label": "Representation",
            "control_type": "buttons",
            "labels": [],
            "frames": [
                {
                    "label": "Observed samples",
                    "points": [
                        {"label": "Sample A", "x": 1, "y": 2, "series": "Class A"},
                        {"label": "Sample B", "x": 3, "y": 4, "series": "Class B"},
                    ],
                    "explanation": "The samples form two visible groups.",
                }
            ],
        },
    )
    heatmap = CanvasBlock(
        id="prediction-errors",
        type="component",
        component_id="prediction-errors",
        component_type="interactive_chart",
        component_ref="prediction-errors.yaml",
        caption="Prediction errors",
        component_data={
            "chart_type": "heatmap",
            "x_label": "Predicted class",
            "y_label": "Actual class",
            "labels": ["Predicted A", "Predicted B"],
            "row_labels": ["Actual A", "Actual B"],
            "frames": [
                {
                    "label": "Validation set",
                    "matrix": [[8, 2], [1, 9]],
                    "explanation": "Most predictions lie on the diagonal.",
                }
            ],
        },
    )
    document = CanvasDocument(
        id="demo-course-lecture-01",
        course_id="demo-course",
        lecture_id="lecture-01",
        title="Demo",
        source_kind="generated",
        source_ref="lecture.pdf",
        workspace_path=str(tmp_path / "canvas" / "index.md"),
        sections=[
            CanvasSection(
                id="visual-analysis",
                title="Visual analysis",
                source_ref="lecture.pdf page 4",
                blocks=[scatter, heatmap],
            )
        ],
    )

    write_document_source(document, tmp_path / "canvas")
    reloaded = read_document_source(tmp_path / "canvas")
    scatter_data = reloaded.sections[0].blocks[0].component_data
    heatmap_data = reloaded.sections[0].blocks[1].component_data

    assert scatter_data is not None
    assert scatter_data.control_type == "buttons"
    assert scatter_data.frames[0].points[1].series == "Class B"
    assert heatmap_data is not None
    assert heatmap_data.row_labels == ["Actual A", "Actual B"]
    assert heatmap_data.frames[0].matrix == [[8.0, 2.0], [1.0, 9.0]]
