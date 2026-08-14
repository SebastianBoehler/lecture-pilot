from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from lecturepilot.canvas_component_catalog import component_spec_issue
from lecturepilot.canvas_models import (
    CanvasBlock,
    CanvasComponentData,
    CanvasComponentFrame,
    CanvasComponentPoint,
    CanvasComponentStep,
    CanvasSection,
    CanvasVisualAnnotation,
    CanvasVisualEdge,
    CanvasVisualNode,
    CanvasVisualSeries,
)
from lecturepilot.models import CanvasSectionPlacement


class StrictProviderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ProviderCanvasComponentPoint(StrictProviderModel):
    label: str
    x: FiniteFloat
    y: FiniteFloat
    series: str | None

    def to_domain(self) -> CanvasComponentPoint:
        return CanvasComponentPoint(label=self.label, x=self.x, y=self.y, series=self.series)


class ProviderCanvasComponentFrame(StrictProviderModel):
    label: str
    values: list[FiniteFloat] = Field(max_length=24)
    points: list[ProviderCanvasComponentPoint] = Field(max_length=120)
    matrix: list[list[FiniteFloat]] = Field(max_length=12)
    explanation: str

    def to_domain(self) -> CanvasComponentFrame:
        return CanvasComponentFrame(
            label=self.label,
            values=self.values,
            points=[point.to_domain() for point in self.points],
            matrix=self.matrix,
            explanation=self.explanation,
        )


class ProviderCanvasComponentStep(StrictProviderModel):
    title: str
    text: str

    def to_domain(self) -> CanvasComponentStep:
        return CanvasComponentStep(title=self.title, text=self.text)


class ProviderCanvasVisualNode(StrictProviderModel):
    id: str
    label: str
    detail: str
    value: str | None = None

    def to_domain(self) -> CanvasVisualNode:
        return CanvasVisualNode(id=self.id, label=self.label, detail=self.detail, value=self.value)


class ProviderCanvasVisualEdge(StrictProviderModel):
    from_id: str
    to_id: str
    label: str | None

    def to_domain(self) -> CanvasVisualEdge:
        return CanvasVisualEdge(from_id=self.from_id, to_id=self.to_id, label=self.label)


class ProviderCanvasVisualSeries(StrictProviderModel):
    label: str
    mark: Literal["line", "bar", "point"]
    points: list[ProviderCanvasComponentPoint] = Field(max_length=24)

    def to_domain(self) -> CanvasVisualSeries:
        return CanvasVisualSeries(
            label=self.label,
            mark=self.mark,
            points=[point.to_domain() for point in self.points],
        )


class ProviderCanvasVisualAnnotation(StrictProviderModel):
    label: str
    target_id: str | None

    def to_domain(self) -> CanvasVisualAnnotation:
        return CanvasVisualAnnotation(label=self.label, target_id=self.target_id)


class ProviderCanvasComponentData(StrictProviderModel):
    chart_type: Literal["bar", "line", "scatter", "heatmap"] | None
    control_type: Literal["buttons", "slider"] | None
    x_label: str | None
    y_label: str | None
    control_label: str | None
    labels: list[str] = Field(max_length=24)
    row_labels: list[str] = Field(max_length=12)
    frames: list[ProviderCanvasComponentFrame] = Field(max_length=12)
    steps: list[ProviderCanvasComponentStep] = Field(max_length=12)
    visual_layout: Literal["flow", "timeline", "grid", "plot"] | None = None
    visual_nodes: list[ProviderCanvasVisualNode] = Field(default_factory=list, max_length=12)
    visual_edges: list[ProviderCanvasVisualEdge] = Field(default_factory=list, max_length=16)
    visual_series: list[ProviderCanvasVisualSeries] = Field(default_factory=list, max_length=6)
    visual_annotations: list[ProviderCanvasVisualAnnotation] = Field(
        default_factory=list, max_length=12
    )

    def to_domain(self) -> CanvasComponentData:
        return CanvasComponentData(
            chart_type=self.chart_type,
            control_type=self.control_type,
            x_label=self.x_label,
            y_label=self.y_label,
            control_label=self.control_label,
            labels=self.labels,
            row_labels=self.row_labels,
            frames=[frame.to_domain() for frame in self.frames],
            steps=[step.to_domain() for step in self.steps],
            visual_layout=self.visual_layout,
            visual_nodes=[node.to_domain() for node in self.visual_nodes],
            visual_edges=[edge.to_domain() for edge in self.visual_edges],
            visual_series=[series.to_domain() for series in self.visual_series],
            visual_annotations=[annotation.to_domain() for annotation in self.visual_annotations],
        )


class ProviderCanvasBlock(StrictProviderModel):
    id: str
    type: Literal[
        "paragraph",
        "list",
        "asset",
        "callout",
        "math",
        "video",
        "checkpoint",
        "quiz",
        "table",
        "component",
    ]
    text: str | None
    items: list[str]
    asset_path: str | None
    asset_url: str | None
    caption: str | None
    answer_index: int | None = Field(ge=0, le=25)
    component_id: str | None
    component_type: (
        Literal[
            "single_choice_quiz",
            "interactive_chart",
            "process_explorer",
            "visual_artifact",
        ]
        | None
    )
    component_ref: str | None
    component_version: int | None = Field(ge=1)
    option_ids: list[str]
    component_data: ProviderCanvasComponentData | None

    @model_validator(mode="after")
    def validate_component_spec(self) -> ProviderCanvasBlock:
        if self.type == "component" and (issue := component_spec_issue(self.to_domain())):
            raise ValueError(f"component {issue}")
        return self

    def to_domain(self) -> CanvasBlock:
        return CanvasBlock(
            id=self.id,
            type=self.type,
            text=self.text,
            items=self.items,
            asset_path=self.asset_path,
            asset_url=self.asset_url,
            caption=self.caption,
            answer_index=self.answer_index,
            component_id=self.component_id,
            component_type=self.component_type,
            component_ref=self.component_ref,
            component_version=self.component_version,
            option_ids=self.option_ids,
            component_data=(self.component_data.to_domain() if self.component_data else None),
        )


class ProviderCanvasSection(StrictProviderModel):
    id: str
    title: str
    source_ref: str | None
    blocks: list[ProviderCanvasBlock]

    def to_domain(self) -> CanvasSection:
        return CanvasSection(
            id=self.id,
            title=self.title,
            source_ref=self.source_ref,
            blocks=[block.to_domain() for block in self.blocks],
        )


class ProviderCanvasSectionPlacement(StrictProviderModel):
    mode: Literal["after_section", "before_section"]
    section_id: str

    def to_domain(self) -> CanvasSectionPlacement:
        return CanvasSectionPlacement(mode=self.mode, section_id=self.section_id)
