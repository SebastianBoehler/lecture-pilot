"""Schema-2 test designs: approved goals with a reviewed AI-owned implementation."""

from datetime import UTC, datetime
from types import SimpleNamespace

from lecturepilot.learning_design.course_learning_intent import (
    LearningIntent,
    LearningIntentApproval,
)
from lecturepilot.learning_design.course_practice_design_context import PracticePlanningContext
from lecturepilot.learning_design.course_practice_design_files import (
    locked_design_file,
    write_design_file,
)
from lecturepilot.learning_design.course_practice_design_models import PracticeDesign
from lecturepilot.learning_design.course_practice_design_review_binding import with_quality_review
from lecturepilot.learning_design.course_practice_target import PracticeTarget
from lecturepilot.core.storage_layout import StorageLayout
from practice_design_review_test_helpers import passing_review

PLANNING_CONTEXT = PracticePlanningContext(
    learner_level="Undergraduate learners in this lecture.",
    prerequisites=["Interpret the supplied evidence."],
    time_budget_minutes=30,
    allowed_aids=["Course notes"],
    assessment_conditions="Complete each assessment individually.",
    insufficiencies=[],
)


def approved_practice_design(
    *,
    course_id: str,
    lecture_id: str,
    source_revision: str,
    targets,
    lecture_title: str = "Practice design",
    objective: str = "Derive the conclusion independently from the cited evidence.",
    planning_context: PracticePlanningContext | dict = PLANNING_CONTEXT,
    approved_by: str = "professor",
    reviewed: bool = True,
    approved: bool = True,
    fixed: bool = False,
) -> PracticeDesign:
    """A schema-2 design: approved goals with a reviewed AI-owned implementation."""
    planning_context = PracticePlanningContext.model_validate(planning_context)
    targets = tuple(PracticeTarget.model_validate(target) for target in targets)
    base = SimpleNamespace(
        source_revision=source_revision,
        objective=objective,
        planning_context=planning_context,
        targets=tuple(targets),
    )
    intent = LearningIntent.from_design(
        base, fixed_target_ids=tuple(target.id for target in targets) if fixed else ()
    )
    if approved:
        intent = intent.model_copy(
            update={
                "approval": LearningIntentApproval(
                    approved_by=approved_by,
                    approved_at=datetime.now(UTC),
                    intent_revision=intent.revision,
                )
            }
        )
    design = PracticeDesign.create(
        course_id=course_id,
        lecture_id=lecture_id,
        lecture_title=lecture_title,
        objective=objective,
        planning_context=planning_context,
        source_revision=source_revision,
        targets=tuple(targets),
        learning_intent=intent,
    )
    return with_quality_review(design, passing_review()) if reviewed else design


def revised_design(design: PracticeDesign, **changes) -> PracticeDesign:
    """An approved replacement (e.g. a professor edit and re-approval) of `design`."""
    values = {
        "course_id": design.course_id,
        "lecture_id": design.lecture_id,
        "lecture_title": design.lecture_title,
        "objective": design.objective,
        "source_revision": design.source_revision,
        "targets": design.targets,
    }
    return approved_practice_design(**{**values, **changes})


def store_design(layout: StorageLayout, design: PracticeDesign) -> PracticeDesign:
    path = layout.lecture_practice_design_path(design.course_id, design.lecture_id)
    with locked_design_file(path):
        write_design_file(path, design)
    return design
