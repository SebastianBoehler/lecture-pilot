from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from lecturepilot.course_practice_design_models import PracticeDesign, PracticeDesignProposal


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
    design: PracticeDesign | PracticeDesignProposal, allowed_source_paths: Iterable[str]
) -> None:
    allowed = set(allowed_source_paths)
    for target in design.targets:
        unknown = set(target.source_refs) - allowed
        if unknown:
            paths = ", ".join(sorted(unknown))
            raise PracticeDesignValidationError(
                f"Practice target {target.id} references unrouted source paths: {paths}."
            )


def validate_canvas_practice_contract(document: _CanvasDocument, design: PracticeDesign) -> None:
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
            if block.type != "checkpoint" or not block.id.startswith("practice-"):
                continue
            target_id = block.id.removeprefix("practice-")
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
        if not section.source_ref:
            raise PracticeDesignValidationError(
                f"Practice checkpoint practice-{target_id} must be in a source-backed section."
            )
        if block.text != target.baseline_task:
            raise PracticeDesignValidationError(
                f"Practice checkpoint practice-{target_id} must use the approved baseline task."
            )
