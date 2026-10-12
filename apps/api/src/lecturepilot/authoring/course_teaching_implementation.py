"""Bounded teaching repair within the existing owned canvas-generation request."""

from anyio import to_thread

from lecturepilot.authoring.authoring_models import AuthoringDesignConflict
from lecturepilot.authoring.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.authoring.authoring_generation_scope import generation_authoring_scope
from lecturepilot.authoring.authoring_runtime import authoring_scope
from lecturepilot.authoring.course_canvas_generation_ownership import (
    require_generation_ownership,
    replace_generation_design,
)
from lecturepilot.authoring.course_canvas_repairs import lecture_source_revision
from lecturepilot.learning_design.course_learning_intent_store import LearningIntentStore
from lecturepilot.learning_design.course_practice_design_models import PracticeDesignProposal
from lecturepilot.learning_design.course_practice_design_review_models import (
    PracticeDesignReviewResult,
)
from lecturepilot.learning_design.course_practice_design_store import PracticeDesignStale
from lecturepilot.courses.course_update_recovery import locked_course_state
from lecturepilot.sources.lecture_source_manifest import read_lecture_source_manifest
from lecturepilot.learning_design.teaching_design_runtime import run_implementation_repair
from lecturepilot.learning_design.course_practice_design_store import PracticeDesignStore


async def repair_implementation(
    app, *, source, design, ownership, feedback=None, reuse_review=False
):
    intent = design.learning_intent
    fixed = {target.id for target in intent.fixed_targets}
    if intent.approval is None or (design.targets and {t.id for t in design.targets} <= fixed):
        # Professor-fixed tasks cannot be repaired by AI; the conflict needs plan review.
        raise AuthoringDesignConflict(
            feedback or "The approved practice design is professor-protected."
        )
    layout = app.state.canvas_workspace.layout
    manifest = read_lecture_source_manifest(
        layout.lecture_source_manifest_path(design.course_id, design.lecture_id),
        design.course_id,
        design.lecture_id,
    )
    paths = tuple(item.path for item in manifest.files)

    def authorize():
        require_generation_ownership(layout, ownership)
        current = PracticeDesignStore(layout).read(
            course_id=design.course_id, lecture_id=design.lecture_id
        )
        if (
            current is None
            or current.revision != design.revision
            or lecture_source_revision(
                layout, course_id=design.course_id, lecture_id=design.lecture_id
            )
            != design.source_revision
        ):
            raise PracticeDesignStale(
                "Course sources or approved goals changed during teaching repair."
            )

    reviewed = await run_implementation_repair(
        planner=app.state.practice_design_planner,
        root=layout.course_root(design.course_id)
        / "builder"
        / "implementation-jobs"
        / design.lecture_id,
        authorize=authorize,
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
        # A design conflict repairs the reviewed implementation without a second review.
        initial_review=PracticeDesignReviewResult(checks=design.quality_review.checks)
        if reuse_review and design.targets
        else None,
    )

    def save():  # The course lock is a blocking file lock: wait for it off the event loop.
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
                repair_reason=feedback,
                proposal=reviewed.proposal,
                review=reviewed.review,
                source=source,
                allowed_source_paths=paths,
            )
            return changed, replace_generation_design(layout, ownership, changed)

    return await to_thread.run_sync(save)


def review_current(design):
    review = design.quality_review
    return review is not None and review.practice_design_revision == design.revision


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
    if not review_current(design):
        design, ownership = await repair_implementation(
            app,
            source=source,
            design=design,
            ownership=ownership,
            feedback="Repair the current implementation before authoring teaching material.",
        )
    previous_revision = None
    for attempt in range(2):
        try:
            with authoring_scope(
                generation_authoring_scope(
                    app,
                    ownership=ownership,
                    source_revision=design.source_revision,
                    session_generation_id=session_generation_id,
                    escalate_design_conflicts=attempt == 0,
                    reuse_design_revision=previous_revision,
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
            if attempt:
                raise
            previous_revision = design.revision
            design, ownership = await repair_implementation(
                app,
                source=source,
                design=design,
                ownership=ownership,
                feedback=str(exc),
                reuse_review=review_current(design),
            )
    raise AssertionError("Unreachable authoring retry state.")
