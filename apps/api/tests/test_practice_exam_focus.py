from datetime import UTC, datetime, timedelta
import json
from types import SimpleNamespace as NS

from lecturepilot.practice_exam_focus import practice_exam_goal_focus

NOW = datetime(2026, 10, 7, tzinfo=UTC)
REV = "a" * 64


def gate(id="g", revision=REV):
    return NS(
        id=id,
        revision=revision,
        title="Empirical risk",
        section_id="risk",
        prompt="HIDDEN_DIAGNOSTIC",
        transfer_prompt="HIDDEN_TRANSFER",
        independent_exit_task="HIDDEN_EXIT",
    )


def test_focus_is_revision_bound_source_scoped_and_does_not_expose_hidden_tasks():
    g = gate()
    weak = NS(independent=False, delayed=False, gate_revision=REV)
    progress = NS(
        goal_evidence={f"g@{REV}": weak},
        delayed_reviews={},
        turns=[
            NS(
                gate_id="g",
                gate_revision=REV,
                attempt_kind="independent",
                gate_status="needs_evidence",
            )
        ],
    )
    rows = practice_exam_goal_focus(
        "lecture-01", NS(gates=[g]), progress, {"lecture-01:risk:definition"}, now=NOW
    )
    assert rows[0]["priority"] == "weak"
    assert rows[0]["source_ids"] == ["lecture-01:risk:definition"]
    assert "HIDDEN" not in json.dumps(rows)
    assert (
        practice_exam_goal_focus(
            "lecture-01",
            NS(gates=[gate(revision="b" * 64)]),
            progress,
            {"lecture-01:risk:definition"},
            now=NOW,
        )
        == []
    )


def test_due_review_is_prioritized_but_supported_only_work_is_not_mastery_evidence():
    progress = NS(
        goal_evidence={},
        turns=[],
        delayed_reviews={
            f"g@{REV}": NS(
                completed_at=None, due_at=NOW - timedelta(days=1), transfer_prompt="HIDDEN_TRANSFER"
            )
        },
    )
    rows = practice_exam_goal_focus(
        "lecture-01", NS(gates=[gate()]), progress, {"lecture-01:risk:definition"}, now=NOW
    )
    assert rows[0]["priority"] == "due"
    progress.delayed_reviews.clear()
    progress.goal_evidence[f"g@{REV}"] = NS(independent=False, delayed=False, supported=True)
    assert (
        practice_exam_goal_focus(
            "lecture-01", NS(gates=[gate()]), progress, {"lecture-01:risk:definition"}, now=NOW
        )
        == []
    )


def test_focus_excludes_unsupported_sections_and_completed_reviews():
    progress = NS(
        goal_evidence={},
        turns=[],
        delayed_reviews={f"g@{REV}": NS(completed_at=NOW, due_at=NOW - timedelta(days=1))},
    )
    assert (
        practice_exam_goal_focus(
            "lecture-01", NS(gates=[gate()]), progress, {"lecture-01:other:definition"}, now=NOW
        )
        == []
    )


def test_generation_prompt_prioritizes_goals_after_required_coverage():
    from lecturepilot.practice_exam_prompt import practice_exam_messages

    messages = practice_exam_messages(
        course_title="ML",
        language="en",
        duration_minutes=90,
        question_count=20,
        course_evidence="[lecture-01:risk:definition] Empirical risk",
        ppi_evidence="",
        learner_focus=[
            {
                "goal_title": "Empirical risk",
                "priority": "weak",
                "source_ids": ["lecture-01:risk:definition"],
            }
        ],
    )
    assert "After covering every available lecture" in messages[0]["content"]
    assert "not proof of mastery" in messages[0]["content"]
    assert "revision-bound study emphasis" in messages[1]["content"]
