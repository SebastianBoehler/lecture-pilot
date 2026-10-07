"""Bounded categorical exam emphasis, without learner text or hidden task wording."""

from datetime import UTC, datetime

from lecturepilot.coaching_state_models import review_key

MAX_EXAM_GOAL_FOCUS = 12


def practice_exam_goal_focus(lecture_id, learning_map, progress, source_ids, *, now=None):
    now = now or datetime.now(UTC)
    focus = []
    for gate in learning_map.gates:
        key = review_key(gate.id, gate.revision)
        evidence = progress.goal_evidence.get(key)
        attempts = [
            t
            for t in progress.turns
            if t.gate_id == gate.id
            and t.gate_revision == gate.revision
            and t.attempt_kind in {"independent", "independent_exit", "delayed_transfer"}
        ]
        weak = bool(attempts and evidence and not (evidence.independent or evidence.delayed))
        review = progress.delayed_reviews.get(key)
        due = bool(review and review.completed_at is None and review.due_at <= now)
        sources = sorted(s for s in source_ids if s.startswith(f"{lecture_id}:{gate.section_id}:"))
        if not sources or not (weak or due):
            continue
        focus.append(
            dict(
                lecture_id=lecture_id,
                goal_id=gate.id,
                gate_revision=gate.revision,
                goal_title=gate.title,
                source_ids=sources[:8],
                priority="weak" if weak else "due",
            )
        )
    return bounded_exam_goal_focus(focus)


def bounded_exam_goal_focus(focus):
    return sorted(
        focus, key=lambda item: (item["priority"] != "weak", item["lecture_id"], item["goal_id"])
    )[:MAX_EXAM_GOAL_FOCUS]
