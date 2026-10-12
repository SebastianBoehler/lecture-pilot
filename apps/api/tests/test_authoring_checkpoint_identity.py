from lecturepilot.authoring.authoring_workspace import AuthoringWorkspace
from practice_design_test_helpers import practice_design_for_canvas
from test_authoring_job import authoring_job


def test_independently_authored_sections_get_lecture_unique_checkpoint_ids(tmp_path):
    job = authoring_job(tmp_path)
    first = job.source.sections[0]
    job.source = job.source.model_copy(
        update={"sections": [first, first.model_copy(update={"id": "second"})]}
    )
    job.design = practice_design_for_canvas(job.source)
    workspace = AuthoringWorkspace(job.root, job.source, job.design, job.authorize)
    text = (
        "A justified conclusion connects relevant evidence to the claim.\n\n"
        '<!-- block id="section-specific-check" type="checkpoint" -->\n'
        ":::checkpoint Evidence check\n"
        "Explain how the evidence supports the conclusion and justify the reasoning.\n:::"
    )
    for path in workspace.paths:
        workspace.write(path, text)
    document = workspace.document()
    ids = [
        block.id
        for section in document.sections
        for block in section.blocks
        if block.type == "checkpoint" and not block.id.startswith("practice-")
    ]
    assert ids == ["section-specific-check", "second-section-specific-check"]
    assert workspace.document() == document


def test_parallel_sections_keep_only_the_first_prediction_card(tmp_path):
    job = authoring_job(tmp_path)
    first = job.source.sections[0]
    job.source = job.source.model_copy(
        update={"sections": [first, first.model_copy(update={"id": "second"})]}
    )
    job.design = practice_design_for_canvas(job.source)
    workspace = AuthoringWorkspace(job.root, job.source, job.design, job.authorize)
    text = (
        '<!-- block id="guess" type="prediction" -->\n'
        ":::prediction Before you begin\nWhy might more evidence change the conclusion?\n:::\n\n"
        "A justified conclusion connects relevant evidence to the claim.\n\n"
        '<!-- block id="check" type="checkpoint" -->\n'
        ":::checkpoint Evidence check\nExplain how the evidence supports the conclusion.\n:::"
    )
    for path in workspace.paths:
        workspace.write(path, text)
    document = workspace.document()
    predictions = [
        (section.source_section_id, block.id)
        for section in document.sections
        for block in section.blocks
        if block.type == "prediction"
    ]
    assert len(predictions) == 1
