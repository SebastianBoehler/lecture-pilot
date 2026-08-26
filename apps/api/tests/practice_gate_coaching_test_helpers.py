from datetime import UTC, datetime

from lecturepilot.coaching_assistance import NextCheck, NextCheckAssistance
from lecturepilot.learning_map import LearningMapGate

IDS = {"user_id": "student-1", "course_id": "course-1", "lecture_id": "lecture-1"}
NOW = datetime(2026, 8, 26, 9, tzinfo=UTC)


def practice_gate(
    *,
    one_hint: bool = False,
    baseline_task: str | None = None,
    independent_exit_task: str | None = None,
    delayed_transfer_task: str | None = None,
) -> LearningMapGate:
    hints = [{"level": "prompt", "content": "Name the invariant first."}]
    if not one_hint:
        hints.append(
            {
                "level": "cue",
                "content": "Check the changed surface against the invariant.",
            }
        )
    return LearningMapGate.create(
        id="practice-mechanism",
        concept_id="mechanism",
        title="Mechanism",
        prompt=baseline_task or "Diagnose the mechanism in the canonical case.",
        target_invariant="The causal boundary remains unchanged.",
        evidence_criteria=[{"id": "boundary", "description": "Names the causal boundary."}],
        transfer_prompt=(
            delayed_transfer_task or "Apply the boundary after the representation changes."
        ),
        independent_exit_task=(
            independent_exit_task or "Apply the boundary to a parallel case without help."
        ),
        independent_exit_surface_change="Change the case details only.",
        delayed_transfer_surface_change="Change the representation and case details.",
        misconceptions=[],
        hint_ladder=hints,
        review_after_days=2,
        section_id="mechanism",
        source_ref="lecture.md",
        practice_target_id="mechanism",
    )


def check(
    gate: LearningMapGate,
    prompt: str | None,
    level: str,
    content: str | None,
) -> NextCheck:
    assert prompt is not None
    return NextCheck(
        gate_id=gate.id,
        gate_revision=gate.revision,
        prompt=prompt,
        assistance=NextCheckAssistance(level=level, content=content),
    )


def assistant_message(next_check: NextCheck | None) -> str:
    if next_check is None:
        return "Assessment recorded."
    content = next_check.assistance.content
    return f"{content + ' ' if content else ''}{next_check.prompt}"
