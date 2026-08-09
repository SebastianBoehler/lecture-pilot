import json
from pathlib import Path

from fastapi.testclient import TestClient

from auth_helpers import professor_headers
from lecturepilot.app import create_app
from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.course_canvas_repairs import lecture_source_revision


def test_professor_edits_approves_and_publishes_the_exact_learning_design(tmp_path: Path) -> None:
    client = _client_with_draft(tmp_path)
    path = _review_path()

    initial = client.get(path, headers=professor_headers())
    assert initial.status_code == 200
    review = initial.json()
    assert len(review["draft_digest"]) == 64
    assert len(review["source_revision"]) == 64
    assert review["approval"] is None
    assert review["factual_quality_separate"] is True
    assert review["warnings"]

    changed = client.put(
        path,
        headers=professor_headers(),
        json={
            "draft_digest": review["draft_digest"],
            "source_revision": review["source_revision"],
            "learning_map_revision": review["learning_map"]["revision"],
            "objective": "Explain the mechanism and transfer it to a changed case.",
            "gates": [
                {
                    "id": "intro-check",
                    "prompt": "Explain the mechanism without using the example wording.",
                    "evidence_criteria": [
                        {
                            "id": "intro-check",
                            "description": "Names the cause and the resulting effect.",
                            "required": True,
                        }
                    ],
                    "transfer_prompt": "Apply the mechanism to an unfamiliar case.",
                    "review_after_days": 4,
                }
            ],
            "prerequisites": [
                {"section_id": "intro", "prerequisite_ids": []},
                {"section_id": "practice", "prerequisite_ids": ["intro"]},
            ],
        },
    )
    assert changed.status_code == 200, changed.json()
    edited = changed.json()
    assert edited["learning_map"]["objective"].startswith("Explain the mechanism")
    assert edited["learning_map"]["gates"][0]["review_after_days"] == 4
    assert edited["learning_map"]["nodes"][1]["prerequisites"] == ["intro"]
    assert edited["approval"] is None

    approved = client.post(
        f"{path}/approve",
        headers=professor_headers(),
        json={
            "draft_digest": edited["draft_digest"],
            "source_revision": edited["source_revision"],
            "learning_map_revision": edited["learning_map"]["revision"],
        },
    )
    assert approved.status_code == 200, approved.json()
    approval = approved.json()["approval"]
    assert approval["approved_by"] == "prof01"
    assert approval["learning_map_revision"] == approved.json()["learning_map"]["revision"]

    published = client.post(_publish_path(), headers=professor_headers())
    assert published.status_code == 200, published.json()
    published_dir = client.app.state.canvas_workspace.course_canvas_store.path(
        "design-course", "lecture-01"
    )
    learning_map = json.loads((published_dir / "learning-map.json").read_text(encoding="utf-8"))
    metadata = json.loads((published_dir / "publication.json").read_text(encoding="utf-8"))
    assert learning_map == approved.json()["learning_map"]
    assert metadata["draft_digest"] == approved.json()["draft_digest"]
    assert metadata["source_revision"] == approved.json()["source_revision"]
    assert metadata["learning_map_revision"] == learning_map["revision"]
    assert metadata["published_by"] == "prof01"
    assert not (published_dir / "learning-design.json").exists()


def test_learning_design_rejects_stale_and_invalid_edits(tmp_path: Path) -> None:
    client = _client_with_draft(tmp_path)
    path = _review_path()
    review = client.get(path, headers=professor_headers()).json()
    valid = _update_payload(review)

    stale_digest = client.put(
        path,
        headers=professor_headers(),
        json={**valid, "draft_digest": "0" * 64},
    )
    stale_revision = client.put(
        path,
        headers=professor_headers(),
        json={**valid, "source_revision": "1" * 64},
    )
    unknown_gate = client.put(
        path,
        headers=professor_headers(),
        json={**valid, "gates": [{**valid["gates"][0], "id": "unknown"}]},
    )
    self_prerequisite = client.put(
        path,
        headers=professor_headers(),
        json={
            **valid,
            "prerequisites": [
                {"section_id": "intro", "prerequisite_ids": ["intro"]},
                {"section_id": "practice", "prerequisite_ids": []},
            ],
        },
    )
    unknown_prerequisite = client.put(
        path,
        headers=professor_headers(),
        json={
            **valid,
            "prerequisites": [
                {"section_id": "intro", "prerequisite_ids": ["unknown"]},
                {"section_id": "practice", "prerequisite_ids": []},
            ],
        },
    )
    duplicate_prerequisite = client.put(
        path,
        headers=professor_headers(),
        json={
            **valid,
            "prerequisites": [
                {"section_id": "intro", "prerequisite_ids": []},
                {"section_id": "practice", "prerequisite_ids": ["intro", "intro"]},
            ],
        },
    )
    cycle = client.put(
        path,
        headers=professor_headers(),
        json={
            **valid,
            "prerequisites": [
                {"section_id": "intro", "prerequisite_ids": ["practice"]},
                {"section_id": "practice", "prerequisite_ids": ["intro"]},
            ],
        },
    )
    bad_interval = client.put(
        path,
        headers=professor_headers(),
        json={
            **valid,
            "gates": [{**valid["gates"][0], "review_after_days": 0}],
        },
    )

    assert stale_digest.status_code == 409
    assert stale_revision.status_code == 409
    assert unknown_gate.status_code == 400
    assert self_prerequisite.status_code == 400
    assert unknown_prerequisite.status_code == 400
    assert duplicate_prerequisite.status_code == 400
    assert cycle.status_code == 400
    assert bad_interval.status_code == 422


def test_regeneration_and_source_change_invalidate_approval(tmp_path: Path) -> None:
    client = _client_with_draft(tmp_path)
    review = client.get(_review_path(), headers=professor_headers()).json()
    approved = client.post(
        f"{_review_path()}/approve",
        headers=professor_headers(),
        json={
            "draft_digest": review["draft_digest"],
            "source_revision": review["source_revision"],
            "learning_map_revision": review["learning_map"]["revision"],
        },
    )
    assert approved.status_code == 200

    workspace = client.app.state.canvas_workspace
    workspace.write_course_canvas_draft(
        _document(title="Regenerated draft"),
        expected_source_revision=_source_revision(workspace),
    )
    regenerated = client.get(_review_path(), headers=professor_headers())
    blocked = client.post(_publish_path(), headers=professor_headers())
    assert regenerated.status_code == 200
    assert regenerated.json()["approval"] is None
    assert regenerated.json()["draft_digest"] != review["draft_digest"]
    assert blocked.status_code == 409

    current = regenerated.json()
    approved_again = client.post(
        f"{_review_path()}/approve",
        headers=professor_headers(),
        json={
            "draft_digest": current["draft_digest"],
            "source_revision": current["source_revision"],
            "learning_map_revision": current["learning_map"]["revision"],
        },
    )
    assert approved_again.status_code == 200
    _write_source_manifest(workspace, source_sha="b" * 64)
    stale_source = client.post(_publish_path(), headers=professor_headers())
    assert stale_source.status_code == 409


def _client_with_draft(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    _write_source_manifest(app.state.canvas_workspace)
    app.state.canvas_workspace.write_course_canvas_draft(
        _document(),
        expected_source_revision=_source_revision(app.state.canvas_workspace),
    )
    return TestClient(app)


def _write_source_manifest(workspace: CanvasWorkspace, *, source_sha: str = "a" * 64) -> None:
    path = workspace.layout.lecture_source_manifest_path("design-course", "lecture-01")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "course_id": "design-course",
                "lecture_id": "lecture-01",
                "files": [{"path": "lecture.md", "sha256": source_sha}],
            }
        ),
        encoding="utf-8",
    )


def _source_revision(workspace: CanvasWorkspace) -> str:
    revision = lecture_source_revision(
        workspace.layout,
        course_id="design-course",
        lecture_id="lecture-01",
    )
    assert revision is not None
    return revision


def _document(*, title: str = "Learning design") -> CanvasDocument:
    return CanvasDocument(
        id="design-course-lecture-01",
        course_id="design-course",
        lecture_id="lecture-01",
        title=title,
        source_kind="generated",
        source_ref="lecture.md",
        workspace_path="course/index.md",
        sections=[
            CanvasSection(
                id="intro",
                title="Mechanism",
                source_ref="lecture.md#mechanism",
                blocks=[
                    CanvasBlock(
                        id="intro-check",
                        type="checkpoint",
                        text="Explain the mechanism.",
                    )
                ],
            ),
            CanvasSection(
                id="practice",
                title="Practice",
                source_ref="lecture.md#practice",
                blocks=[CanvasBlock(id="practice-p", type="paragraph", text="Apply it.")],
            ),
        ],
    )


def _update_payload(review: dict) -> dict:
    return {
        "draft_digest": review["draft_digest"],
        "source_revision": review["source_revision"],
        "learning_map_revision": review["learning_map"]["revision"],
        "objective": review["learning_map"]["objective"],
        "gates": [
            {
                "id": gate["id"],
                "prompt": gate["prompt"],
                "evidence_criteria": gate["evidence_criteria"],
                "transfer_prompt": gate["transfer_prompt"],
                "review_after_days": gate["review_after_days"],
            }
            for gate in review["learning_map"]["gates"]
        ],
        "prerequisites": [
            {"section_id": node["section_id"], "prerequisite_ids": node["prerequisites"]}
            for node in review["learning_map"]["nodes"]
        ],
    }


def _review_path() -> str:
    return "/admin/courses/design-course/lectures/lecture-01/canvas/learning-design"


def _publish_path() -> str:
    return "/admin/courses/design-course/lectures/lecture-01/canvas/publish"
