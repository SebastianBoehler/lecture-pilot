from __future__ import annotations

from lecturepilot.canvas.canvas_models import CanvasSection


def is_student_section(section: CanvasSection) -> bool:
    return section.source_ref == "student workspace" or section.id.startswith("student-")
