from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.canvas_models import (
    CanvasBlock,
    CanvasComponentData,
    CanvasComponentFrame,
    CanvasComponentPoint,
    CanvasComponentStep,
    CanvasSection,
)
from lecturepilot.models import CanvasSectionPlacement


class StrictProviderModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ProviderCanvasComponentPoint(StrictProviderModel):
    label: str
    x: float
    y: float
    series: str | None

    def to_domain(self) -> CanvasComponentPoint:
        return CanvasComponentPoint(label=self.label, x=self.x, y=self.y, series=self.series)


class ProviderCanvasComponentFrame(StrictProviderModel):
    label: str
    values: list[float] = Field(max_length=24)
    points: list[ProviderCanvasComponentPoint] = Field(max_length=120)
    matrix: list[list[float]] = Field(max_length=12)
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
    component_type: Literal["single_choice_quiz", "interactive_chart", "process_explorer"] | None
    component_ref: str | None
    component_version: int | None = Field(ge=1)
    option_ids: list[str]
    component_data: ProviderCanvasComponentData | None

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
