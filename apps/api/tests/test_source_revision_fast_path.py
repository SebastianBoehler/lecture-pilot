from auth_helpers import professor_headers
from practice_design_route_test_helpers import design_path
from test_learning_intent_routes import goal_client

from lecturepilot.sources import course_builder_source


def test_readiness_and_approval_hash_sources_without_importing_documents(tmp_path, monkeypatch):
    api, _ = goal_client(tmp_path)
    design = api.post(design_path() + "/intent/proposal", headers=professor_headers()).json()

    def no_import(*args, **kwargs):
        raise AssertionError("Revision checks must not parse or import source documents.")

    monkeypatch.setattr(course_builder_source, "_derive_source_document", no_import)
    readiness = api.get(design_path() + "/readiness", headers=professor_headers())
    assert readiness.status_code == 200, readiness.text
    assert readiness.json()["current_source_revision"] == design["source_revision"]
    approved = api.post(
        design_path() + "/intent/approve",
        headers=professor_headers(),
        json={
            "source_revision": design["source_revision"],
            "practice_design_revision": design["revision"],
        },
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["learning_intent"]["approval"]

    # Starting a draft is a revision check too; the parse runs later in the background job.
    started = api.post(
        design_path().removesuffix("/practice-design") + "/canvas/draft",
        headers={
            **professor_headers(),
            "Idempotency-Key": "fast-path-draft-start",
            "Prefer": "respond-async",
            "X-LecturePilot-Client-Contract": "1",
        },
    )
    assert started.status_code == 202, started.text
