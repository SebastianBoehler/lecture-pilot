"""Export a learner's own generated lecture notes as one Markdown document."""

from __future__ import annotations

import re
from pathlib import Path

from lecturepilot.canvas_markdown import CanvasMarkdownError, read_section_frontmatter
from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.canvas_snapshot import locked_canvas_access
from lecturepilot.learner_canvas_markdown import (
    place_student_sections,
    read_student_section_placements,
    read_student_sections,
)

_BLOCK_MARKER = re.compile(r"^<!-- block [^>]*-->\s*$", re.MULTILINE)
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class LearnerNotesExportError(RuntimeError):
    pass


def export_learner_notes(published: CanvasDocument, *, canvas_dir: Path) -> str | None:
    """Return the learner's notes in canvas placement order, or None when there are none."""
    student_dir = canvas_dir / "student"
    with locked_canvas_access(canvas_dir):
        if not student_dir.is_dir() or student_dir.is_symlink():
            return None
        try:
            sections = read_student_sections(
                canvas_dir,
                course_id=published.course_id,
                lecture_id=published.lecture_id,
            )
            if not sections:
                return None
            ordered = place_student_sections(
                published.sections, sections, read_student_section_placements(canvas_dir)
            )
            bodies = _section_bodies(student_dir)
        except (CanvasMarkdownError, OSError, TypeError, ValueError) as exc:
            raise LearnerNotesExportError("Your notes for this lecture could not be read.") from exc
    student_ids = {section.id for section in sections}
    parts = [f"# {published.title}"]
    for section in ordered:
        if section.id not in student_ids or section.id not in bodies:
            continue
        parts.append(f"## {section.title}\n\n{bodies[section.id]}".rstrip())
    return "\n\n".join(parts) + "\n"


def notes_filename(lecture_id: str) -> str:
    stem = _SAFE_NAME.sub("-", lecture_id).strip(".-")[:80] or "lecture"
    return f"lecturepilot-notes-{stem}.md"


def _section_bodies(student_dir: Path) -> dict[str, str]:
    bodies: dict[str, str] = {}
    for path in sorted(student_dir.glob("*.md")):
        if path.is_symlink() or not path.is_file():
            continue
        section_id = read_section_frontmatter(path).get("id")
        if isinstance(section_id, str):
            bodies[section_id] = _body(path.read_text(encoding="utf-8"))
    return bodies


def _body(text: str) -> str:
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        text = text[end + 4 :] if end != -1 else text
    return re.sub(r"\n{3,}", "\n\n", _BLOCK_MARKER.sub("", text)).strip()
