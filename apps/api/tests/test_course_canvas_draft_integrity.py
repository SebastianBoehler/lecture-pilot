from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from auth_helpers import professor_headers
from canvas_workspace_fixtures import published_course_canvas
from lecturepilot.app import create_app
from lecturepilot.canvas_models import MAX_SOURCE_REF_LENGTH, CanvasDocument
from lecturepilot.canvas_workspace import CanvasWorkspace
from lecturepilot.client_contract import CLIENT_CONTRACT_HEADER, CLIENT_CONTRACT_VERSION
from lecturepilot.course_canvas_errors import CanvasGenerationRepairableError
from lecturepilot.course_canvas_plan_parser import planned_document as _planned_document
from lecturepilot.course_canvas_store import CourseCanvasStore, InvalidCanvasDraftError
from lecturepilot.storage_layout import StorageLayout


def test_planned_source_ref_preserves_bounded_source_evidence() -> None:
    source_ref = "s" * MAX_SOURCE_REF_LENGTH
    source = published_course_canvas("demo-course", "lecture-01").model_copy(
        update={"source_kind": "markdown", "source_ref": source_ref}
    )

    result = _planned_document(
        {
            "sections": [
                {
                    "id": "introduction",
                    "title": "Introduction",
                    "source_ref": source_ref,
                    "blocks": [{"type": "paragraph", "text": "Source-backed detail."}],
                }
            ]
        },
        source,
    )

    validated = CanvasDocument.model_validate(result.model_dump())
    assert validated.source_ref == source_ref
    assert len(validated.source_ref) == MAX_SOURCE_REF_LENGTH


def test_invalid_draft_does_not_replace_existing_draft(tmp_path: Path) -> None:
    store = CourseCanvasStore(StorageLayout(tmp_path / "workspaces"))
    existing = published_course_canvas("demo-course", "lecture-01")
    store.write_draft(existing)
    invalid = existing.model_copy(
        update={
            "title": "Invalid replacement",
            "source_ref": "s" * (MAX_SOURCE_REF_LENGTH + 1),
        }
    )

    with pytest.raises(InvalidCanvasDraftError):
        store.write_draft(invalid)

    preserved = store.read_draft(course_id="demo-course", lecture_id="lecture-01")
    assert preserved is not None
    assert preserved.title == existing.title
    assert preserved.source_ref == existing.source_ref


def test_generation_rejects_invalid_draft_without_replacing_existing(
    tmp_path: Path,
) -> None:
    client = _course_client(tmp_path)
    existing = published_course_canvas("draft-integrity", "lecture-01")
    client.app.state.canvas_workspace.write_course_canvas_draft(existing)
    client.app.state.course_planner = _InvalidCoursePlanner()

    response = client.post(
        "/admin/courses/draft-integrity/lectures/lecture-01/canvas/draft",
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "draft-request-key-invalid-0001",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Generated canvas draft is invalid and was not saved."
    preview = client.get(
        "/admin/courses/draft-integrity/lectures/lecture-01/canvas/draft",
        headers=professor_headers(),
    )
    assert preview.status_code == 200
    assert preview.json()["title"] == existing.title


def test_generation_requires_a_valid_idempotency_key(tmp_path: Path) -> None:
    client = _course_client(tmp_path)
    path = "/admin/courses/draft-integrity/lectures/lecture-01/canvas/draft"

    missing = client.post(path, headers={**professor_headers(), **_client_contract_headers()})
    invalid = client.post(
        path,
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "too-short",
        },
    )

    assert missing.status_code == 400
    assert missing.json()["detail"] == "Idempotency-Key header is required."
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "Idempotency-Key must be 16-128 URL-safe characters."


def test_stale_client_is_rejected_before_generation_work(tmp_path: Path) -> None:
    client = _course_client(tmp_path)
    planner = _UnexpectedCoursePlanner()
    client.app.state.course_planner = planner

    response = client.post(
        "/admin/courses/draft-integrity/lectures/lecture-01/canvas/draft",
        headers={
            **professor_headers(),
            "Idempotency-Key": "draft-request-key-stale-0001",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "code": "client_update_required",
        "detail": "LecturePilot was updated. Reload this page to continue.",
    }
    assert response.headers[CLIENT_CONTRACT_HEADER] == CLIENT_CONTRACT_VERSION
    assert planner.called is False
    generations = (
        client.app.state.canvas_workspace.layout.course_root("draft-integrity")
        / "builder"
        / "generations"
    )
    assert not generations.exists()


def test_invalid_stored_draft_returns_actionable_error(tmp_path: Path) -> None:
    client = _course_client(tmp_path)
    workspace = client.app.state.canvas_workspace
    workspace.write_course_canvas_draft(published_course_canvas("draft-integrity", "lecture-01"))
    manifest = (
        workspace.course_canvas_store.draft_path("draft-integrity", "lecture-01") / "index.md"
    )
    source = manifest.read_text(encoding="utf-8")
    source_ref_line = 'source_ref: "test fixture"'
    assert source_ref_line in source
    invalid_source_ref = "s" * (MAX_SOURCE_REF_LENGTH + 1)
    manifest.write_text(
        source.replace(
            source_ref_line,
            f'source_ref: "{invalid_source_ref}"',
        ),
        encoding="utf-8",
    )

    preview = client.get(
        "/admin/courses/draft-integrity/lectures/lecture-01/canvas/draft",
        headers=professor_headers(),
    )
    publish = client.post(
        "/admin/courses/draft-integrity/lectures/lecture-01/canvas/publish",
        headers=professor_headers(),
    )

    expected = "Stored canvas draft is invalid. Retry generation for this lecture."
    assert preview.status_code == 500
    assert preview.json()["detail"] == expected
    assert publish.status_code == 500
    assert publish.json()["detail"] == expected


def test_ai_repair_uses_and_persists_failure_guidance_for_the_source_revision(
    tmp_path: Path,
) -> None:
    client = _course_client(tmp_path)
    planner = _RepairingCoursePlanner()
    client.app.state.course_planner = planner
    draft_path = "/admin/courses/draft-integrity/lectures/lecture-01/canvas/draft"

    failed = client.post(
        draft_path,
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "draft-request-key-repair-failure-0001",
        },
    )
    missing_draft = client.get(draft_path, headers=professor_headers())
    repaired = client.post(
        f"{draft_path}/repair",
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "draft-request-key-repair-success-0001",
        },
    )
    regenerated = client.post(
        draft_path,
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "draft-request-key-repair-regenerate-0001",
        },
    )
    source_path = (
        client.app.state.canvas_workspace.layout.course_uploads_dir("draft-integrity")
        / "Lecture01.tex"
    )
    source_path.write_bytes(
        b"""
\\title{Draft integrity revised}
\\begin{frame}{Changed source}
This revised source evidence changes the lecture fingerprint while remaining valid.
\\end{frame}
"""
    )
    invalidated = client.post(
        draft_path,
        headers={
            **professor_headers(),
            **_client_contract_headers(),
            "Idempotency-Key": "draft-request-key-repair-invalidated-0001",
        },
    )

    assert failed.status_code == 503
    assert failed.headers["X-Generation-Repairable"] == "true"
    assert missing_draft.status_code == 404
    assert missing_draft.headers["X-Generation-Repairable"] == "true"
    assert missing_draft.json()["detail"] == (
        "Math block risk-equation uses unsupported command \\P."
    )
    assert repaired.status_code == 200
    assert regenerated.status_code == 200
    assert invalidated.status_code == 503
    assert planner.repair_contexts == [
        None,
        "Math block risk-equation uses unsupported command \\P.",
        "Math block risk-equation uses unsupported command \\P.",
        None,
    ]
    repair_record = (
        client.app.state.canvas_workspace.layout.course_root("draft-integrity")
        / "builder"
        / "repairs"
        / "lecture-01.json"
    )
    assert repair_record.exists()
    assert "source_revision" in repair_record.read_text(encoding="utf-8")


def _course_client(tmp_path: Path) -> TestClient:
    app = create_app()
    app.state.canvas_workspace = CanvasWorkspace(
        workspace_root=tmp_path / "workspaces",
        material_root=tmp_path / "materials",
    )
    client = TestClient(app)
    created = client.post(
        "/admin/course-workspaces",
        json={
            "course_title": "Draft Integrity",
            "lecture_number": "01",
            "lecture_title": "Introduction",
        },
        headers=professor_headers(),
    )
    assert created.status_code == 200
    upload = client.post(
        "/admin/courses/draft-integrity/materials",
        data={"path": "Lecture01.tex"},
        files={
            "file": (
                "Lecture01.tex",
                b"""
\\title{Draft integrity}
\\begin{frame}{Introduction}
Source evidence explains the generated canvas contract in sufficient detail.
\\end{frame}
""",
            )
        },
        headers=professor_headers(),
    )
    assert upload.status_code == 200
    return client


class _InvalidCoursePlanner:
    async def plan_canvas(
        self,
        source_document: CanvasDocument,
        *,
        output_language: str,
    ) -> CanvasDocument:
        return source_document.model_copy(
            update={
                "source_kind": "generated",
                "source_ref": "s" * (MAX_SOURCE_REF_LENGTH + 1),
            }
        )


class _RepairingCoursePlanner:
    def __init__(self) -> None:
        self.repair_contexts: list[str | None] = []

    async def plan_canvas(
        self,
        source_document: CanvasDocument,
        *,
        repair_context: str | None = None,
        output_language: str,
    ) -> CanvasDocument:
        self.repair_contexts.append(repair_context)
        if repair_context is None:
            raise CanvasGenerationRepairableError(
                "Math block risk-equation uses unsupported command \\P."
            )
        return source_document.model_copy(
            update={
                "source_kind": "generated",
                "source_ref": "Repaired from source evidence",
            }
        )


class _UnexpectedCoursePlanner:
    called = False

    async def plan_canvas(
        self,
        source_document: CanvasDocument,
        *,
        output_language: str,
    ) -> CanvasDocument:
        self.called = True
        raise AssertionError("stale clients must not start canvas planning")


def _client_contract_headers() -> dict[str, str]:
    return {CLIENT_CONTRACT_HEADER: CLIENT_CONTRACT_VERSION}
