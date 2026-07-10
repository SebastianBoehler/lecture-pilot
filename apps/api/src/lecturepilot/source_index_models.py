from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from lecturepilot.source_bundle import SourceBundleFile


class IndexedSourceFile(BaseModel):
    path: str = Field(min_length=1, max_length=500)
    kind: str = Field(min_length=1, max_length=80)
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    modified_ns: int = Field(ge=0)
    status: Literal["indexed"] = "indexed"

    def as_bundle_file(self) -> SourceBundleFile:
        return SourceBundleFile(path=self.path, kind=self.kind, size_bytes=self.size_bytes)


class CourseSourceIndex(BaseModel):
    schema_version: int = 1
    course_id: str = Field(min_length=1, max_length=120)
    files: list[IndexedSourceFile] = Field(default_factory=list)
