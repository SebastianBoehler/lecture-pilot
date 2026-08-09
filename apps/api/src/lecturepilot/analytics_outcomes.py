from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MIN_OUTCOME_CELL_SIZE = 5

AnalyticsDataStatus = Literal["available", "insufficient_data"]
AnalyticsVersionStatus = Literal["current", "historical"]


class AnalyticsOutcomeCell(BaseModel):
    evidence_type: str
    sample_size: int = Field(ge=0)
    data_status: AnalyticsDataStatus
    rate: float | None = Field(default=None, ge=0, le=1)


def outcome_cell(evidence_type: str, outcomes: dict[str, bool]) -> AnalyticsOutcomeCell:
    sample_size = len(outcomes)
    available = sample_size >= MIN_OUTCOME_CELL_SIZE
    return AnalyticsOutcomeCell(
        evidence_type=evidence_type,
        sample_size=sample_size,
        data_status="available" if available else "insufficient_data",
        rate=(round(sum(outcomes.values()) / sample_size, 4) if available else None),
    )


def version_status(
    publication_version: int,
    current_publication_version: int,
) -> AnalyticsVersionStatus:
    if publication_version == current_publication_version:
        return "current"
    return "historical"


def version_sort_key(publication_version: int, status: AnalyticsVersionStatus) -> tuple[int, int]:
    rank = {"current": 0, "historical": 1}[status]
    return rank, -publication_version
