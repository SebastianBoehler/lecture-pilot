from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
    ]
    text: str | None = None
    items: list[str] = Field(default_factory=list)
    asset_path: str | None = Field(default=None, max_length=500)
    asset_url: str | None = Field(default=None, max_length=500)
    caption: str | None = Field(default=None, max_length=500)
    answer_index: int | None = Field(default=None, ge=0, le=25)


class CanvasSection(BaseModel):
    id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    source_ref: str | None = Field(default=None, max_length=500)
    blocks: list[CanvasBlock] = Field(default_factory=list)


class CanvasDocument(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    import_version: int = Field(default=1, ge=1)
    course_id: str = Field(min_length=1, max_length=120)
    lecture_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    source_kind: Literal["latex", "markdown", "generated"]
    source_ref: str = Field(min_length=1, max_length=500)
    workspace_path: str = Field(min_length=1, max_length=500)
    sections: list[CanvasSection] = Field(default_factory=list)
