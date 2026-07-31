from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class NormalizedPpiFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=240)
    text_path: str = Field(min_length=1, max_length=260)
    media_type: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)
    character_count: int = Field(ge=0)


class PpiExamSourceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^ppi-[0-9]+$")
    ppi_lecture_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=300)
    protocol_count: int = Field(ge=0)
    imported_at: datetime
    borrowed_until: str | None = Field(default=None, max_length=120)
    source_filename: str = Field(min_length=1, max_length=240)
    archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    files: list[NormalizedPpiFile] = Field(min_length=1, max_length=80)


class PpiCredentials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=80)
    password: SecretStr


class PpiImportInput(PpiCredentials):
    ppi_lecture_id: int = Field(gt=0)
    confirm_token_spend: bool = False


class PpiCatalogLecture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(gt=0)
    title: str
    protocol_count: int = Field(ge=0)
    borrowed: bool
    can_borrow: bool
    download_available: bool
    borrowed_until: str | None = None
    cached_source_id: str | None = None


class PpiCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tokens: int = Field(ge=0)
    lectures: list[PpiCatalogLecture]
    cached_sources: list[PpiExamSourceManifest]


class PpiImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: PpiExamSourceManifest
    token_spent: bool
    reused: bool

    @model_validator(mode="after")
    def coherent_result(self) -> "PpiImportResult":
        if self.reused and self.token_spent:
            raise ValueError("A reused PPI source cannot spend a token.")
        return self
