from hashlib import sha256
import json

from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.course_canvas_section_checkpoints import SectionPlanCheckpointStore
from lecturepilot.course_canvas_section_planner import plan_sections_individually
from practice_design_test_helpers import practice_design_for_canvas
from test_course_canvas_section_concurrency import (
    _SectionOnlyPlanClient,
    _settings,
    _source_document,
)


async def test_retry_replans_legacy_checkpoint_without_source_section_identity(tmp_path) -> None:
    source = _source_document(1)
    design = practice_design_for_canvas(source)
    settings = _settings()
    checkpoints = SectionPlanCheckpointStore(
        tmp_path / "sections.json", source_revision="source-revision-1"
    )
    legacy_key = sha256(
        "\0".join(
            (
                "3",
                settings.model,
                "en",
                design.revision,
                source.sections[0].model_dump_json(),
            )
        ).encode()
    ).hexdigest()
    legacy_section = CanvasSection(
        id="learning-source-1",
        title="Learning source-1",
        source_ref="Lecture.tex frame 1",
        blocks=[
            CanvasBlock(
                id="learning-source-1-paragraph-1",
                type="paragraph",
                text="Legacy source-backed explanation retained before exact identity existed.",
            ),
            CanvasBlock(
                id="learning-source-1-checkpoint-1",
                type="checkpoint",
                text="Explain the source-backed mechanism and its resulting failure mode.",
            ),
        ],
    )
    checkpoints.path.write_text(
        json.dumps(
            {
                "source_revision": "source-revision-1",
                "sections": {legacy_key: legacy_section.model_dump(mode="json")},
            }
        ),
        encoding="utf-8",
    )
    client = _SectionOnlyPlanClient()

    planned = await plan_sections_individually(
        model_client=client,
        settings=settings,
        source_document=source,
        practice_design=design,
        checkpoint_store=checkpoints,
    )

    assert client.source_ids == ["source-1"]
    assert planned.sections[0].source_section_id == "source-1"
