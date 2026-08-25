from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_prompt import source_evidence
from lecturepilot.course_practice_design_models import PracticeDesignProposal


def practice_design_messages(
    source: CanvasDocument,
    *,
    source_revision: str,
    allowed_source_paths: Sequence[str],
) -> list[dict[str, str]]:
    paths = ", ".join(allowed_source_paths)
    return [
        {
            "role": "system",
            "content": (
                "You are the LecturePilot practice-design planner. Return only the requested "
                "structured proposal for one lecture. Propose 3 to 6 targets when the evidence "
                "supports them; do not pad thin material or split one skill into cosmetic targets. "
                "Every target must state an observable independent capability, one source-grounded "
                "baseline task, a distinct parallel independent-exit task, and a changed-surface "
                "delayed-transfer task that preserves the reasoning. Give precise evidence criteria, "
                "diagnostic misconceptions, and only progressive approved hints. Use exact source "
                "paths from the supplied authoritative list; never invent a path or cite an extracted "
                "frame as a source path."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Authoritative source revision: {source_revision}\n"
                f"Allowed exact source paths: {paths}\n\n{source_evidence(source)}"
            ),
        },
    ]


def practice_design_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "lecturepilot_practice_design",
            "strict": True,
            "schema": PracticeDesignProposal.model_json_schema(),
        },
    }
