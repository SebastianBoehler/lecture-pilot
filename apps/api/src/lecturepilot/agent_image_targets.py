from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from lecturepilot.agent_canvas_write import find_student_canvas_section_path
from lecturepilot.canvas_markdown import read_document_source, read_student_section_placements
from lecturepilot.canvas_models import CanvasSection
from lecturepilot.canvas_signatures import is_student_section


_GENERIC_TERMS = {
    "and",
    "canvas",
    "compact",
    "create",
    "das",
    "der",
    "diagram",
    "die",
    "eine",
    "explain",
    "generated",
    "image",
    "infographic",
    "section",
    "show",
    "teaching",
    "the",
    "this",
    "visual",
    "visualize",
    "with",
}


@dataclass(frozen=True)
class ImageSectionTarget:
    section: CanvasSection
    path: Path


def resolve_image_section_target(
    canvas_dir: Path,
    *,
    requested_section_id: str | None,
    focused_section_id: str | None,
    prompt: str,
) -> ImageSectionTarget | None:
    document = read_document_source(canvas_dir)
    student_dir = canvas_dir / "student"
    candidates = [
        ImageSectionTarget(section=section, path=path)
        for section in document.sections
        if is_student_section(section)
        if (path := find_student_canvas_section_path(student_dir, section.id)) is not None
    ]
    if not candidates:
        return None

    by_id = {candidate.section.id: candidate for candidate in candidates}
    for section_id in (requested_section_id, focused_section_id):
        if section_id and section_id in by_id:
            return by_id[section_id]

    placements = read_student_section_placements(canvas_dir)
    for anchor_id in (requested_section_id, focused_section_id):
        anchored = [
            candidate
            for candidate in candidates
            if anchor_id and placements.get(candidate.section.id, {}).get("section_id") == anchor_id
        ]
        if len(anchored) == 1:
            return anchored[0]
        if anchored and (
            match := _semantic_match(
                anchored,
                prompt=prompt,
                requested_section_id=requested_section_id,
                focused_section=_section_by_id(document.sections, focused_section_id),
            )
        ):
            return match

    return _semantic_match(
        candidates,
        prompt=prompt,
        requested_section_id=requested_section_id,
        focused_section=_section_by_id(document.sections, focused_section_id),
    )


def _semantic_match(
    candidates: list[ImageSectionTarget],
    *,
    prompt: str,
    requested_section_id: str | None,
    focused_section: CanvasSection | None,
) -> ImageSectionTarget | None:
    prompt_terms = _terms(prompt)
    requested_terms = _terms(requested_section_id or "")
    focused_terms = _section_terms(focused_section) if focused_section else set()
    scored = [
        (
            6 * len(requested_terms & _identity_terms(candidate.section))
            + 3 * len(prompt_terms & _identity_terms(candidate.section))
            + len(prompt_terms & _section_terms(candidate.section))
            + 4 * len(focused_terms & _identity_terms(candidate.section)),
            candidate,
        )
        for candidate in candidates
    ]
    best_score = max((score for score, _ in scored), default=0)
    best = [candidate for score, candidate in scored if score == best_score]
    return best[0] if best_score >= 3 and len(best) == 1 else None


def _section_by_id(sections: list[CanvasSection], section_id: str | None) -> CanvasSection | None:
    return next((section for section in sections if section.id == section_id), None)


def _identity_terms(section: CanvasSection) -> set[str]:
    return _terms(f"{section.id} {section.title}")


def _section_terms(section: CanvasSection) -> set[str]:
    values = [section.id, section.title]
    for block in section.blocks:
        values.extend([block.text or "", block.caption or "", *block.items])
    return _terms(" ".join(values))


def _terms(value: str) -> set[str]:
    return {
        term
        for term in re.findall(r"[a-z0-9]+", value.casefold())
        if len(term) >= 3 and term not in _GENERIC_TERMS
    }
