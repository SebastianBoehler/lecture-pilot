"""Bounded teaching repair within the existing owned canvas-generation request."""

from lecturepilot.authoring_models import AuthoringDesignConflict
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.authoring_generation_scope import generation_authoring_scope
from lecturepilot.authoring_runtime import authoring_scope
from lecturepilot.course_canvas_generation_ownership import (
    require_generation_ownership,
    replace_generation_design,
)
from lecturepilot.course_canvas_repairs import lecture_source_revision
from lecturepilot.course_learning_intent_store import LearningIntentStore
from lecturepilot.course_practice_design_models import PracticeDesignProposal
from lecturepilot.course_practice_design_store import PracticeDesignStale
from lecturepilot.course_update_recovery import locked_course_state
from lecturepilot.lecture_source_manifest import read_lecture_source_manifest


async def repair_implementation(app, *, source, design, ownership, feedback=None):
    intent = design.learning_intent
    if intent is None or design.approval is not None or intent.approval is None:
        raise AuthoringDesignConflict(
            feedback or "The full practice design is professor-protected."
        )
    layout = app.state.canvas_workspace.layout
    manifest = read_lecture_source_manifest(
        layout.lecture_source_manifest_path(design.course_id, design.lecture_id),
        design.course_id,
        design.lecture_id,
    )
    paths = tuple(item.path for item in manifest.files)
    reviewed = await app.state.practice_design_planner.propose(
        source=source,
        source_revision=design.source_revision,
        allowed_source_paths=paths,
        initial=PracticeDesignProposal(
            **{
                key: getattr(design, key)
                for key in (
                    "lecture_title",
                    "objective",
                    "planning_context",
                    "targets",
                )
            }
        )
        if design.targets
        else None,
        protected_intent=intent,
        repair_context=feedback,
    )
    with locked_course_state(layout.course_root(design.course_id)):
        require_generation_ownership(layout, ownership)
        if (
            lecture_source_revision(
                layout, course_id=design.course_id, lecture_id=design.lecture_id
            )
            != design.source_revision
        ):
            raise PracticeDesignStale("Course sources changed during teaching repair.")
        changed = LearningIntentStore(layout).save_implementation(
            expected=design,
            proposal=reviewed.proposal,
            review=reviewed.review,
            source=source,
            allowed_source_paths=paths,
        )
        owner = replace_generation_design(layout, ownership, changed)
    return changed, owner


async def author_with_implementation(
    app,
    *,
    source,
    design,
    ownership,
    output_language,
    repair_context=None,
    session_generation_id=None,
):
    review = design.quality_review
    if (
        design.learning_intent
        and design.approval is None
        and (review is None or review.has_critical_issues)
    ):
        design, ownership = await repair_implementation(
            app,
            source=source,
            design=design,
            ownership=ownership,
            feedback="Repair the current implementation before authoring teaching material.",
        )
    for attempt in range(2):
        try:
            with authoring_scope(
                generation_authoring_scope(
                    app,
                    ownership=ownership,
                    source_revision=design.source_revision,
                    session_generation_id=session_generation_id,
                )
            ):
                arguments = {"practice_design": design, "output_language": output_language}
                if repair_context:
                    arguments["repair_context"] = repair_context
                document = await app.state.course_planner.plan_canvas(source, **arguments)
            return document, design, ownership
        except CanvasGenerationRepairableError as exc:
            raise exc.with_source_revision(design.source_revision).with_practice_design_revision(
                design.revision
            )
        except AuthoringDesignConflict as exc:
            if attempt or design.learning_intent is None or design.approval is not None:
                raise
            design, ownership = await repair_implementation(
                app,
                source=source,
                design=design,
                ownership=ownership,
                feedback=str(exc),
            )
    raise AssertionError("Unreachable authoring retry state.")
