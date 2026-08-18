from __future__ import annotations

import json
import re

from lecturepilot.assessment_prompts import assessment_generation_instruction
from lecturepilot.canvas_component_catalog import component_catalog_instruction
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.course_canvas_language import canvas_language_instruction
from lecturepilot.course_canvas_math import generated_math_instructions
from lecturepilot.course_canvas_repair_preflight import repair_failure_constraint


def repair_messages(
    source: CanvasDocument,
    section: CanvasSection,
    target: CanvasBlock | None,
    failure: str,
    *,
    output_language: str,
) -> list[dict[str, str]]:
    scope = (
        "Return one section whose blocks array contains only replacement blocks for the failed "
        "block. Do not repeat or rewrite unchanged blocks. You may replace one mixed prose/math "
        "block with a paragraph or callout followed by a clean math block."
        if target
        else "Return one complete replacement section without changing its topic."
    )
    return [
        {
            "role": "system",
            "content": (
                "You are applying a surgical patch to a generated LecturePilot canvas. "
                f"{canvas_language_instruction(output_language)} "
                f"{scope} Return JSON only, with exactly this outer shape: "
                '{"sections":[{"id":"same-section-id","title":"same title",'
                '"source_ref":"same source reference","blocks":[...]}]}. '
                "Each replacement block must include type, text, items, asset_path, caption, "
                "answer_index, component_id, component_type, component_ref, component_version, "
                "option_ids, and component_data, using null or [] when a field does not apply. "
                f"{component_catalog_instruction()} "
                "Preserve the meaning and use only the supplied evidence. "
                f"{assessment_generation_instruction()} "
                f"{repair_failure_constraint(failure)} "
                f"{generated_math_instructions()}"
            ),
        },
        {
            "role": "user",
            "content": "\n\n".join(
                [
                    f"Validation failure:\n{failure}",
                    f"Failed section context:\n{_section_context(section, target)}",
                    f"Failed block:\n{target.model_dump_json() if target else 'whole section'}",
                    f"Relevant professor source evidence:\n{_source_evidence(source, section)}",
                ]
            ),
        },
    ]


def repair_retry_message(error: str, target: CanvasBlock | None) -> dict[str, str]:
    scope = "only replacement blocks" if target else "one complete replacement section"
    return {
        "role": "user",
        "content": (
            f"The proposed patch failed validation: {error} "
            f"Return corrected structured JSON containing {scope}."
        ),
    }


def _section_context(section: CanvasSection, target: CanvasBlock | None) -> str:
    if target is None:
        return section.model_dump_json()
    return json.dumps(
        {
            "id": section.id,
            "title": section.title,
            "source_ref": section.source_ref,
            "blocks": [{"id": block.id, "type": block.type} for block in section.blocks],
        },
        separators=(",", ":"),
    )


def _source_evidence(source: CanvasDocument, target: CanvasSection) -> str:
    target_terms = _terms(f"{target.title} {target.source_ref or ''}")
    ranked = sorted(
        source.sections,
        key=lambda section: len(
            target_terms & _terms(f"{section.title} {section.source_ref or ''}")
        ),
        reverse=True,
    )
    evidence = "\n\n".join(section.model_dump_json() for section in ranked[:3])
    return evidence[:24_000]


def _terms(value: str) -> set[str]:
    return {token.lower() for token in re.findall(r"[A-Za-z0-9]+", value) if len(token) > 3}
