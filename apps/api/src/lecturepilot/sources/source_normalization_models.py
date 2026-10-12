from __future__ import annotations

from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field


class SourceLocator(BaseModel):
    page: int | None = Field(default=None, ge=1)
    slide: int | None = Field(default=None, ge=1)
    sheet: str | None = Field(default=None, min_length=1, max_length=120)
    cell_range: str | None = Field(default=None, min_length=1, max_length=80)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    bbox: tuple[float, float, float, float] | None = None


class NormalizedCell(BaseModel):
    row: int = Field(ge=1)
    column: int = Field(ge=1)
    value: str | float | bool | None = None
    formula: str | None = Field(default=None, max_length=2_000)


class NormalizedBlock(BaseModel):
    kind: Literal["heading", "paragraph", "table", "formula", "code", "image", "link"]
    text: str | None = Field(default=None, max_length=60_000)
    asset_path: str | None = Field(default=None, min_length=1, max_length=500)
    url: AnyHttpUrl | None = None
    cells: list[NormalizedCell] = Field(default_factory=list, max_length=10_000)
    locator: SourceLocator
    extraction: Literal["native", "rendered", "ocr"]


class NormalizedDocument(BaseModel):
    schema_version: Literal[1]
    source_path: str = Field(min_length=1, max_length=500)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: str = Field(min_length=1, max_length=200)
    blocks: list[NormalizedBlock] = Field(default_factory=list, max_length=10_000)
    warnings: list[str] = Field(default_factory=list, max_length=100)
