from lecturepilot.authoring_models import AuthoringMetrics
from lecturepilot.authoring_tools import AuthoringTools
from lecturepilot.authoring_workspace import AuthoringWorkspace
from practice_design_test_helpers import practice_design_for_canvas
from test_authoring_job import authoring_job


async def test_duplicate_checkpoint_ids_are_repairable_before_authoring_acceptance(tmp_path):
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
    actions = AuthoringTools(job, workspace, AuthoringMetrics())

    rejected = await actions.validate()
    assert rejected["valid"] is False
    assert "Duplicate checkpoint ID 'section-specific-check'" in str(rejected["issues"])
    assert actions.accepted_digest is None

    actions.edit("/draft/second.md", 'id="section-specific-check"', 'id="second-check"')
    accepted = await actions.validate()
    assert accepted["valid"] is True
    assert actions.accepted_digest == workspace.digest()
