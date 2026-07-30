from lecturepilot.canvas_models import (
    CanvasBlock,
    CanvasComponentData,
    CanvasComponentFrame,
    CanvasDocument,
    CanvasSection,
)
from lecturepilot.canvas_signatures import official_canvas_signature


def _document(value: float) -> CanvasDocument:
    return CanvasDocument(
        id="course-lecture-01",
        course_id="course",
        lecture_id="lecture-01",
        title="Lecture 01",
        source_kind="generated",
        source_ref="source.md",
        workspace_path="/tmp/index.md",
        sections=[
            CanvasSection(
                id="risk",
                title="Risk",
                blocks=[
                    CanvasBlock(
                        id="risk-chart",
                        type="component",
                        component_id="risk-chart",
                        component_type="interactive_chart",
                        component_ref="components/risk-chart.yaml",
                        component_version=1,
                        component_data=CanvasComponentData(
                            chart_type="bar",
                            labels=["Reject", "Classify"],
                            frames=[
                                CanvasComponentFrame(
                                    label="1x",
                                    values=[value, 0.4],
                                    explanation="The threshold changes with cost.",
                                )
                            ],
                        ),
                    )
                ],
            )
        ],
    )


def test_official_canvas_signature_includes_component_data() -> None:
    assert official_canvas_signature(_document(0.6)) != official_canvas_signature(_document(0.8))
