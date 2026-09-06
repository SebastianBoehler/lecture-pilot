from __future__ import annotations

from collections.abc import Iterable
import re
from typing import Protocol

from lecturepilot.course_practice_design_models import PracticeDesign, PracticeDesignProposal
from lecturepilot.course_practice_design_evidence import (
    PracticeSourceAnchor,
    target_source_anchors,
)
from lecturepilot.course_practice_design_review_models import PracticeDesignReviewResult
from lecturepilot.course_source_ownership import routed_source_owner


class PracticeDesignValidationError(ValueError):
    """Raised when a design cannot be grounded in the lecture contract."""


class _CanvasBlock(Protocol):
    id: str
    type: str
    text: str | None


class _CanvasSection(Protocol):
    source_ref: str | None
    blocks: list[_CanvasBlock]


class _CanvasDocument(Protocol):
    sections: list[_CanvasSection]


def validate_practice_design(
    design: PracticeDesign | PracticeDesignProposal,
    *,
    source: _CanvasDocument,
    allowed_source_paths: Iterable[str],
) -> None:
    allowed = set(allowed_source_paths)
    for target in design.targets:
        anchors = target_source_anchors(target)
        unknown = {anchor.source_path for anchor in anchors} - allowed
        if unknown:
            paths = ", ".join(sorted(unknown))
            raise PracticeDesignValidationError(
                f"Practice target {target.id} references unrouted source paths: {paths}."
            )
        for anchor in anchors:
            _validate_source_anchor(anchor, source, allowed)


def validate_source_anchors(
    anchors: Iterable[PracticeSourceAnchor],
    *,
    source: _CanvasDocument,
    allowed_source_paths: Iterable[str],
) -> None:
    allowed = set(allowed_source_paths)
    for anchor in anchors:
        if anchor.source_path not in allowed:
            raise PracticeDesignValidationError(
                f"Source anchor references unrouted source path: {anchor.source_path}."
            )
        _validate_source_anchor(anchor, source, allowed)


def validate_practice_design_review(
    review: PracticeDesignReviewResult,
    design: PracticeDesign | PracticeDesignProposal,
    *,
    source: _CanvasDocument,
    allowed_source_paths: Iterable[str],
) -> None:
    target_ids = {target.id for target in design.targets}
    unknown = {
        target_id
        for check in review.checks
        for target_id in check.target_ids
        if target_id not in target_ids
    }
    if unknown:
        raise PracticeDesignValidationError(
            f"Semantic review references unknown practice targets: {', '.join(sorted(unknown))}."
        )
    validate_source_anchors(
        (anchor for check in review.checks for anchor in check.supporting_anchors),
        source=source,
        allowed_source_paths=allowed_source_paths,
    )


def _validate_source_anchor(
    anchor: PracticeSourceAnchor,
    source: _CanvasDocument,
    routed_paths: set[str],
) -> None:
    if any(
        source_anchor_matches_section(anchor, section, routed_paths) for section in source.sections
    ):
        return
    raise PracticeDesignValidationError(
        f"Source anchor for {anchor.source_path} is not a verbatim excerpt from that routed source."
    )


def source_anchor_matches_section(
    anchor: PracticeSourceAnchor,
    section: _CanvasSection,
    routed_paths: set[str],
) -> bool:
    return routed_source_owner(
        section.source_ref, routed_paths
    ) == anchor.source_path and _normalize_whitespace(anchor.excerpt) in _section_text(section)


def _section_text(section: _CanvasSection) -> str:
    values: list[str] = []
    title = getattr(section, "title", None)
    if title:
        values.append(title)
    for block in section.blocks:
        for value in (
            block.text,
            getattr(block, "caption", None),
            *getattr(block, "items", ()),
        ):
            if value:
                values.append(value)
    return _normalize_whitespace(" ".join(values))


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def validate_canvas_practice_contract(
    document: _CanvasDocument,
    design: PracticeDesign,
    *,
    expected_source_sections: dict[str, str] | None = None,
) -> None:
    """Validate canonical target checkpoints without importing canvas models.

    The document needs sections with ``source_ref`` and blocks with ``id``,
    ``type``, and ``text``. Later canvas contract fields can be checked here
    without making practice-design models depend on the canvas package.
    """

    expected = {target.id: target for target in design.targets}
    checkpoints: dict[str, list[tuple[_CanvasSection, _CanvasBlock]]] = {
        target_id: [] for target_id in expected
    }
    unknown: list[str] = []
    for section in document.sections:
        for block in section.blocks:
            if not block.id.startswith("practice-"):
                continue
            target_id = block.id.removeprefix("practice-")
            if block.type != "checkpoint":
                raise PracticeDesignValidationError(
                    f"Practice block id {block.id} may only be a checkpoint."
                )
            if target_id not in expected:
                unknown.append(target_id)
            else:
                checkpoints[target_id].append((section, block))

    if unknown:
        raise PracticeDesignValidationError(
            f"Canvas claims unknown practice targets: {', '.join(sorted(set(unknown)))}."
        )
    for target_id, target in expected.items():
        matches = checkpoints[target_id]
        if len(matches) != 1:
            raise PracticeDesignValidationError(
                f"Canvas needs exactly one practice-{target_id} checkpoint."
            )
        section, block = matches[0]
        if (
            expected_source_sections is not None
            and getattr(section, "source_section_id", None) != expected_source_sections[target_id]
        ):
            raise PracticeDesignValidationError(
                f"Practice checkpoint practice-{target_id} must remain in its exact "
                "anchor-bearing source section."
            )
        if routed_source_owner(section.source_ref, set(target.source_refs)) is None:
            raise PracticeDesignValidationError(
                f"Practice checkpoint practice-{target_id} must be in a section owned by its "
                "approved source evidence."
            )
        if block.text != target.baseline_task:
            raise PracticeDesignValidationError(
                f"Practice checkpoint practice-{target_id} must use the approved baseline task."
            )


def validate_learning_map_practice_contract(learning_map, design: PracticeDesign) -> None:
    from lecturepilot.learning_map_practice_validation import (
        validate_learning_map_practice_contract as validate,
    )

    validate(learning_map, design)
