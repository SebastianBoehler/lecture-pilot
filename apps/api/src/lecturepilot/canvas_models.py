from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat


MAX_SOURCE_REF_LENGTH = 500


class CanvasComponentPoint(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    x: FiniteFloat
    y: FiniteFloat
    series: str | None = Field(default=None, max_length=120)


class CanvasComponentFrame(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    values: list[FiniteFloat] = Field(default_factory=list, max_length=24)
    points: list[CanvasComponentPoint] = Field(default_factory=list, max_length=120)
    matrix: list[list[FiniteFloat]] = Field(default_factory=list, max_length=12)
    explanation: str = Field(min_length=1, max_length=500)


class CanvasComponentStep(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    text: str = Field(min_length=1, max_length=800)


class CanvasVisualNode(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    label: str = Field(min_length=1, max_length=120)
    detail: str = Field(min_length=1, max_length=500)
    value: str | None = Field(default=None, max_length=80)


class CanvasVisualEdge(BaseModel):
    from_id: str = Field(min_length=1, max_length=80)
    to_id: str = Field(min_length=1, max_length=80)
    label: str | None = Field(default=None, max_length=120)


class CanvasVisualSeries(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    mark: Literal["line", "bar", "point"]
    points: list[CanvasComponentPoint] = Field(default_factory=list, max_length=24)


class CanvasVisualAnnotation(BaseModel):
    label: str = Field(min_length=1, max_length=300)
    target_id: str | None = Field(default=None, max_length=80)


class CanvasComponentData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chart_type: Literal["bar", "line", "scatter", "heatmap"] | None = None
    control_type: Literal["buttons", "slider"] | None = None
    x_label: str | None = Field(default=None, max_length=120)
    y_label: str | None = Field(default=None, max_length=120)
    control_label: str | None = Field(default=None, max_length=120)
    labels: list[str] = Field(default_factory=list, max_length=24)
    row_labels: list[str] = Field(default_factory=list, max_length=12)
    frames: list[CanvasComponentFrame] = Field(default_factory=list, max_length=12)
    steps: list[CanvasComponentStep] = Field(default_factory=list, max_length=12)
    visual_layout: Literal["flow", "timeline", "grid", "plot"] | None = None
    visual_nodes: list[CanvasVisualNode] = Field(default_factory=list, max_length=12)
    visual_edges: list[CanvasVisualEdge] = Field(default_factory=list, max_length=16)
    visual_series: list[CanvasVisualSeries] = Field(default_factory=list, max_length=6)
    visual_annotations: list[CanvasVisualAnnotation] = Field(default_factory=list, max_length=12)


class CanvasBlock(BaseModel):
    id: str = Field(min_length=1, max_length=120)
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
    text: str | None = None
    items: list[str] = Field(default_factory=list)
    asset_path: str | None = Field(default=None, max_length=500)
    asset_url: str | None = Field(default=None, max_length=500)
    caption: str | None = Field(default=None, max_length=500)
    answer_index: int | None = Field(default=None, ge=0, le=25)
    component_id: str | None = Field(default=None, max_length=120)
    component_type: str | None = Field(default=None, max_length=120)
    component_ref: str | None = Field(default=None, max_length=240)
    component_version: int | None = Field(default=None, ge=1)
    option_ids: list[str] = Field(default_factory=list, max_length=26)
    component_data: CanvasComponentData | None = None


class CanvasSection(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    source_ref: str | None = Field(default=None, max_length=MAX_SOURCE_REF_LENGTH)
    practice_exam_eligible: bool = True
    blocks: list[CanvasBlock] = Field(default_factory=list)


class CanvasDocument(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    import_version: int = Field(default=1, ge=1)
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    source_kind: Literal["latex", "markdown", "generated"]
    source_ref: str = Field(min_length=1, max_length=MAX_SOURCE_REF_LENGTH)
    workspace_path: str = Field(min_length=1, max_length=500)
    sections: list[CanvasSection] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list, max_length=20)
