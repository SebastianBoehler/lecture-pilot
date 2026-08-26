from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from pydantic import Field, field_validator

from lecturepilot.course_practice_design_contract import (
    NonblankText,
    StrictPracticeDesignModel,
)


class PracticeSourceAnchor(StrictPracticeDesignModel):
    source_path: NonblankText = Field(
        min_length=1,
        max_length=500,
        description="Exact path from the authoritative routed source-path list.",
    )
    excerpt: NonblankText = Field(
        min_length=1,
        max_length=1_600,
        description=(
            "Bounded verbatim source excerpt. Whitespace may be normalized, but wording and "
            "symbols must occur in the exact routed CanvasDocument source path."
        ),
    )

    @field_validator("excerpt", mode="before")
    @classmethod
    def normalize_excerpt_whitespace(cls, value: object) -> object:
        return " ".join(value.split()) if isinstance(value, str) else value


class _AnchoredItem(Protocol):
    source_anchor: PracticeSourceAnchor | None


class _AnchoredTarget(Protocol):
    outcome_anchor: PracticeSourceAnchor
    target_invariant_anchor: PracticeSourceAnchor
    baseline_task_anchor: PracticeSourceAnchor
    independent_exit_task_anchor: PracticeSourceAnchor
    delayed_transfer_task_anchor: PracticeSourceAnchor
    evidence_criteria: Iterable[_AnchoredItem]
    misconceptions: Iterable[_AnchoredItem]
    hint_ladder: Iterable[_AnchoredItem]


def target_source_anchors(target: _AnchoredTarget) -> tuple[PracticeSourceAnchor, ...]:
    direct = (
        target.outcome_anchor,
        target.target_invariant_anchor,
        target.baseline_task_anchor,
        target.independent_exit_task_anchor,
        target.delayed_transfer_task_anchor,
    )
    nested = tuple(
        item.source_anchor
        for items in (target.evidence_criteria, target.misconceptions, target.hint_ladder)
        for item in items
        if item.source_anchor is not None
    )
    return (*direct, *nested)


def anchored_source_paths(target: _AnchoredTarget) -> tuple[str, ...]:
    return tuple(dict.fromkeys(anchor.source_path for anchor in target_source_anchors(target)))
