"""Atomic professor-intent approval and fenced unpublished implementation changes."""

from datetime import UTC, datetime

from lecturepilot.course_learning_intent import LearningIntent, LearningIntentApproval
from lecturepilot.course_practice_design_files import locked_design_file, write_design_file
from lecturepilot.course_practice_design_models import PracticeDesign
from lecturepilot.course_practice_design_review_binding import with_quality_review
from lecturepilot.course_practice_design_store import PracticeDesignStore, PracticeDesignStale
from lecturepilot.course_practice_design_validation import (
    validate_practice_design,
    validate_practice_design_review,
)


class LearningIntentStore(PracticeDesignStore):
    def save_goals(
        self,
        *,
        expected,
        course_id,
        lecture_id,
        source_revision,
        proposal,
        source,
        allowed_source_paths,
    ):
        from lecturepilot.course_learning_intent_proposal import validate_goal_evidence

        validate_goal_evidence(proposal, source=source, allowed_source_paths=allowed_source_paths)
        changed = PracticeDesign.create(
            course_id=course_id,
            lecture_id=lecture_id,
            source_revision=source_revision,
            lecture_title=proposal.lecture_title,
            objective=proposal.objective,
            planning_context=proposal.planning_context,
            targets=(),
            learning_intent=proposal.intent(source_revision),
        )
        if expected and expected.learning_intent and expected.source_revision == source_revision:
            if [goal.id for goal in proposal.goals] != [
                goal.id for goal in expected.learning_intent.goals
            ]:
                raise ValueError(
                    "Protected goal identities cannot be added, removed or reordered during editing."
                )
            if expected.targets:
                from lecturepilot.course_practice_design_evidence import anchored_source_paths
                from lecturepilot.course_practice_target import PracticeTarget

                targets = []
                for previous, goal in zip(expected.targets, proposal.goals, strict=True):
                    target = previous.model_copy(update=goal.model_dump(mode="python"))
                    target = PracticeTarget.model_validate(
                        {
                            **target.model_dump(mode="python"),
                            "source_refs": anchored_source_paths(target),
                        }
                    )
                    targets.append(target)
                changed = rebuild(changed, targets=tuple(targets))
                intent = LearningIntent.from_design(
                    changed,
                    fixed_target_ids=tuple(
                        target.id for target in expected.learning_intent.fixed_targets
                    ),
                )
                changed = rebuild(changed, learning_intent=intent)
        path = self._path(course_id, lecture_id)
        with locked_design_file(path):
            current = self._read(path, course_id, lecture_id)
            if current != expected:
                raise PracticeDesignStale("Learning goals changed. Reload them.")
            if (
                current is not None
                and current.approval is not None
                and current.source_revision == source_revision
            ):
                raise ValueError(
                    "Existing full approval requires explicit conversion before editing goals."
                )
            write_design_file(path, changed)
        return changed

    def approve(
        self,
        *,
        course_id,
        lecture_id,
        source_revision,
        design_revision,
        approved_by,
        fixed_target_ids=(),
        convert_legacy=False,
    ):
        path = self._path(course_id, lecture_id)
        with locked_design_file(path):
            current = self._required(path, course_id, lecture_id)
            if current.source_revision != source_revision or current.revision != design_revision:
                raise PracticeDesignStale("Learning goals or sources changed. Reload them.")
            if current.approval is not None and not convert_legacy:
                raise ValueError(
                    "Existing full approval requires explicit conversion to goal approval."
                )
            intent = LearningIntent.from_design(current, fixed_target_ids=fixed_target_ids)
            intent = intent.model_copy(
                update={
                    "approval": LearningIntentApproval(
                        approved_by=approved_by,
                        approved_at=datetime.now(UTC),
                        intent_revision=intent.revision,
                    )
                }
            )
            changed = rebuild(current, learning_intent=intent)
            if current.quality_review:
                changed = with_quality_review(changed, current.quality_review)
            write_design_file(path, changed)
            return changed

    def save_implementation(self, *, expected, proposal, review, source, allowed_source_paths):
        path = self._path(expected.course_id, expected.lecture_id)
        with locked_design_file(path):
            current = self._required(path, expected.course_id, expected.lecture_id)
            if current != expected:
                raise PracticeDesignStale("Learning goals or implementation changed during repair.")
            intent = current.learning_intent
            if current.approval is not None or intent is None or intent.approval is None:
                raise ValueError(
                    "Only an AI-owned implementation with approved goals can be repaired."
                )
            intent.require_matches(proposal)
            changed = rebuild(current, **proposal.model_dump(mode="python"))
            validate_practice_design(
                changed, source=source, allowed_source_paths=allowed_source_paths
            )
            validate_practice_design_review(
                review, changed, source=source, allowed_source_paths=allowed_source_paths
            )
            if any(check.severity == "critical" for check in review.checks):
                raise ValueError("Implementation repair still has critical semantic issues.")
            changed = with_quality_review(changed, review)
            write_design_file(path, changed)
            return changed


def rebuild(current, **changes):
    return PracticeDesign.create(
        **{
            **current.model_dump(mode="python", exclude={"revision", "quality_review", "approval"}),
            **changes,
        }
    )
