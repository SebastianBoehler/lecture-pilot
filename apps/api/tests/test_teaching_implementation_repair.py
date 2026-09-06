from types import SimpleNamespace

import pytest

from lecturepilot.authoring_models import AuthoringDesignConflict
from lecturepilot.course_canvas_generation_ownership import (
    begin_owned_generation_source,
    revoke_generation_ownership,
)
from lecturepilot.course_learning_intent_store import LearningIntentStore
from lecturepilot.course_practice_design_planner import ReviewedPracticeDesignProposal
from lecturepilot.course_practice_design_store import PracticeDesignStore
from lecturepilot.course_teaching_implementation import author_with_implementation
from practice_design_test_helpers import passing_review, source_document
from test_practice_design_generation_preflight import (
    _app,
    _save_design,
    _write_manifest,
    COURSE_ID,
    LECTURE_ID,
)


@pytest.mark.anyio
@pytest.mark.parametrize("racing", [None, "source", "cancel", "goal"])
async def test_confirmed_conflict_repairs_owned_implementation_and_fences_races(tmp_path, racing):
    app = _app(tmp_path)
    _write_manifest(app, "a" * 64)
    design = _save_design(app, approved=False)
    layout = app.state.canvas_workspace.layout
    design = LearningIntentStore(layout).approve(
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        source_revision=design.source_revision,
        design_revision=design.revision,
        approved_by="professor",
    )
    evidence = source_document(
        text=(
            "Source evidence. Among 200 patients, 80 have the condition. Of 60 positive predictions, "
            "48 are correct. Precision is correct positive predictions divided by positive predictions; "
            "recall is correct positive predictions divided by patients with the condition."
        )
    ).model_copy(update={"course_id": COURSE_ID, "lecture_id": LECTURE_ID})
    source, _, design, owner = begin_owned_generation_source(
        layout,
        layout.course_root(COURSE_ID),
        lambda *_: evidence,
        course_id=COURSE_ID,
        lecture_id=LECTURE_ID,
        generation_id="c" * 32,
        attempt=1,
    )
    authored = []

    async def plan_canvas(source, *, practice_design, **kwargs):
        authored.append(practice_design)
        if len(authored) == 1:
            raise AuthoringDesignConflict("The generated diagnostic has contradictory counts.")
        return source

    async def repair(**kwargs):
        assert kwargs["protected_intent"] == design.learning_intent
        if racing == "source":
            _write_manifest(app, "b" * 64)
        if racing == "cancel":
            revoke_generation_ownership(
                layout,
                SimpleNamespace(
                    course_id=COURSE_ID,
                    lecture_id=LECTURE_ID,
                    generation_id=owner.generation_id,
                    attempt=owner.attempt,
                ),
            )
        if racing == "goal":
            LearningIntentStore(layout).approve(
                course_id=COURSE_ID,
                lecture_id=LECTURE_ID,
                source_revision=design.source_revision,
                design_revision=design.revision,
                approved_by="professor",
                fixed_target_ids=(design.targets[0].id,),
            )
        initial = kwargs["initial"]
        changed = initial.model_copy(
            update={
                "targets": (
                    initial.targets[0].model_copy(
                        update={
                            "baseline_task": "Among 200 patients, 80 have the condition. Of 60 positive predictions, 48 are correct. Calculate precision and recall.",
                        }
                    ),
                )
            }
        )
        return ReviewedPracticeDesignProposal(changed, passing_review())

    app.state.course_planner = SimpleNamespace(plan_canvas=plan_canvas)
    app.state.practice_design_planner = SimpleNamespace(propose=repair)
    operation = author_with_implementation(
        app, source=source, design=design, ownership=owner, output_language="en"
    )
    if racing:
        with pytest.raises((ValueError, RuntimeError), match="changed|superseded"):
            await operation
        assert len(authored) == 1
    else:
        _, changed, changed_owner = await operation
        assert len(authored) == 2
        assert changed.learning_intent == design.learning_intent
        assert changed.revision != design.revision
        assert changed_owner.practice_design_revision == changed.revision
        assert 48 / 60 == 0.8 and 48 / 80 == 0.6
        assert (
            PracticeDesignStore(layout).read(course_id=COURSE_ID, lecture_id=LECTURE_ID) == changed
        )
