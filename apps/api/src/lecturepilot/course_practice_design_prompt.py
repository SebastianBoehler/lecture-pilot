from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from lecturepilot.canvas_models import CanvasDocument
from lecturepilot.course_canvas_prompt import source_evidence
from lecturepilot.course_practice_design_models import PracticeDesignProposal
from lecturepilot.model_provider_schema import strict_pydantic_response_format


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
                "structured proposal for one lecture. Optimize for delayed, unaided performance of "
                "the approved capability; assisted completion, engagement, speed, and confidence are "
                "not evidence of learning. Select the minimum set of distinct capabilities supported "
                "by the source; do not pad thin material or split one skill into cosmetic targets. "
                "Work backward from source-supported outcomes to acceptable evidence and practice. "
                "For each target, state the target invariant held constant across every variant. "
                "Diagnostic attempt means baseline_task before substantive help, used to choose "
                "support and never alone as mastery evidence. Independent exit means a parallel task "
                "after support, issued unaided and hidden during instruction. Delayed transfer means "
                "a later changed-form task preserving the invariant. Describe each controlled surface "
                "change and require no new unprovided knowledge. Atomic evidence criteria each test one "
                "observable part of learner work, never keyword presence; at least one must be required "
                "and required criteria must cover the invariant. Misconceptions stay within the target "
                "boundary: name plausible incorrect reasoning and an observable diagnostic cue, not "
                "unrelated errors or unstated prerequisites. Approved hints reveal only the minimum "
                "next information: prompt asks the learner to inspect or plan without domain answer "
                "content; cue names the relevant principle or representation, not the next answer; "
                "faded_example supplies an analogous partial example with a learner-owned step; "
                "worked_step gives one justified step and returns a new step to the learner. Prefill "
                "the professor-editable planning context only from supplied evidence. For every "
                "unsupported context field, return null plus exactly one explicit insufficiency; never "
                "invent learner level, prerequisites, time budget, allowed aids, or assessment "
                "conditions. review_after_days is an operational proposal informed by available "
                "context, not a claim that this interval is scientifically optimal. Use exact source "
                "paths from the supplied authoritative list. For every outcome, invariant, task, "
                "required criterion, misconception, and present hint, return its exact source path "
                "and a bounded verbatim excerpt from that path; whitespace may be normalized but "
                "wording and symbols may not be paraphrased. source_refs must be the ordered unique "
                "paths used by those field anchors. Never invent a path or cite an extracted frame "
                "as a source path."
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
    return strict_pydantic_response_format(
        name="lecturepilot_practice_design", model=PracticeDesignProposal
    )
