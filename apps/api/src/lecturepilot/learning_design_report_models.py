from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator


CoverageStatus = Literal["complete", "incomplete", "not_applicable"]
DiagnosticCode = Literal[
    "assessment_section_source_missing",
    "concept_without_assessment",
    "inferred_linear_prerequisite",
    "no_source_backed_assessment",
    "quiz_only_no_open_checkpoint",
    "worked_example_after_assessment",
]


class LearningDesignCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    covered: int = Field(ge=0)
    total: int = Field(ge=0)
    status: CoverageStatus

    @model_validator(mode="after")
    def validate_counts(self) -> LearningDesignCoverage:
        expected: CoverageStatus
        if self.total == 0:
            expected = "not_applicable"
        elif self.covered == self.total:
            expected = "complete"
        else:
            expected = "incomplete"
        if self.covered > self.total or self.status != expected:
            raise ValueError("Learning-design coverage counts are inconsistent.")
        return self


class LearningDesignSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    total_concepts: int = Field(ge=0)
    concepts_with_gate: int = Field(ge=0)
    concepts_with_quiz: int = Field(ge=0)
    concepts_with_assessment: int = Field(ge=0)


class LearningDesignCoverageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    gate_concepts: LearningDesignCoverage
    quiz_concepts: LearningDesignCoverage
    source_backed_assessments: LearningDesignCoverage
    transfer_prompts: LearningDesignCoverage


class LearningDesignConceptReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    section_id: str = Field(min_length=1, max_length=160)
    title: str = Field(min_length=1, max_length=200)
    gate_ids: list[str] = Field(max_length=100)
    quiz_ids: list[str] = Field(max_length=100)
    source_backed_assessment_ids: list[str] = Field(max_length=200)


class LearningDesignDiagnosticCoordinates(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    section_id: str | None = Field(default=None, min_length=1, max_length=160)
    assessment_id: str | None = Field(default=None, min_length=1, max_length=160)
    block_id: str | None = Field(default=None, min_length=1, max_length=160)
    prerequisite_section_id: str | None = Field(default=None, min_length=1, max_length=160)


class LearningDesignDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    id: str = Field(min_length=66, max_length=160, pattern=r"^[a-z_]+:[a-f0-9]{64}$")
    code: DiagnosticCode
    message: str = Field(min_length=1, max_length=500)
    action: str = Field(min_length=1, max_length=500)
    coordinates: LearningDesignDiagnosticCoordinates


class LearningDesignReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1]
    draft_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    learning_map_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    summary: LearningDesignSummary
    coverage: LearningDesignCoverageSummary
    concepts: list[LearningDesignConceptReport] = Field(max_length=200)
    diagnostics: list[LearningDesignDiagnostic] = Field(max_length=200)
    report_revision: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_revision(self, info: ValidationInfo) -> LearningDesignReport:
        if not (info.context or {}).get("build_revision"):
            expected = learning_design_report_revision(self)
            if self.report_revision != expected:
                raise ValueError("Learning-design report revision is invalid.")
        return self

    @classmethod
    def create(cls, **values: object) -> LearningDesignReport:
        proposal = cls.model_validate(
            {**values, "report_revision": "0" * 64}, context={"build_revision": True}
        )
        payload = proposal.model_dump(mode="json", exclude={"report_revision"})
        return cls.model_validate({**payload, "report_revision": _digest(payload)})


def learning_design_report_revision(report: LearningDesignReport) -> str:
    return _digest(report.model_dump(mode="json", exclude={"report_revision"}))


def _digest(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
