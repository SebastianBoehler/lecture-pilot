from __future__ import annotations

from lecturepilot.canvas_models import CanvasDocument, CanvasSection


def is_student_section(section: CanvasSection) -> bool:
    return section.source_ref == "student workspace" or section.id.startswith("student-")


def official_canvas_signature(document: CanvasDocument):
    return [
        (
            section.id,
            section.title,
            section.source_ref,
            [
                (
                    block.id,
                    block.type,
                    block.text,
                    tuple(block.items),
                    block.asset_path,
                    block.asset_url,
                    block.caption,
                    block.component_id,
                    block.component_type,
                    block.component_ref,
                    block.component_version,
                    tuple(block.option_ids),
                )
                for block in section.blocks
            ],
        )
        for section in document.sections
        if not is_student_section(section)
    ]
