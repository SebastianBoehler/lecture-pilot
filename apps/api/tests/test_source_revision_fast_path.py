from auth_helpers import professor_headers
from practice_design_route_test_helpers import design_path
from test_learning_intent_routes import goal_client

from lecturepilot import course_builder_source


def test_readiness_and_approval_hash_sources_without_importing_documents(tmp_path, monkeypatch):
    api, _ = goal_client(tmp_path)
    design = api.post(design_path() + "/intent/proposal", headers=professor_headers()).json()

    def no_import(*args, **kwargs):
        raise AssertionError("Revision checks must not parse or import source documents.")

    monkeypatch.setattr(course_builder_source, "_course_builder_source_document_locked", no_import)
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
