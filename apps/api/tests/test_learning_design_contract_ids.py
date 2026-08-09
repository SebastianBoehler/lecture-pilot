from pathlib import Path

import pytest

from auth_helpers import professor_headers
from lecturepilot.canvas_markdown import write_document_source
from lecturepilot.canvas_models import CanvasBlock, CanvasSection
from lecturepilot.course_canvas_store import CourseCanvasStore, InvalidCanvasDraftError
from lecturepilot.storage_layout import StorageLayout
from test_learning_design_review_routes import (
    _client_with_draft,
    _document,
    _review_path,
    _update_payload,
)


@pytest.mark.parametrize("duplicate", ["section", "checkpoint"])
def test_draft_write_rejects_duplicate_learning_contract_ids(
    tmp_path: Path,
    duplicate: str,
) -> None:
    document = _document()
    if duplicate == "section":
        document.sections[1] = document.sections[1].model_copy(update={"id": "intro"})
    else:
        document.sections[1] = document.sections[1].model_copy(
            update={
                "blocks": [
                    CanvasBlock(
                        id="intro-check",
                        type="checkpoint",
                        text="A second checkpoint with the same id.",
                    )
                ]
            }
        )

    with pytest.raises(InvalidCanvasDraftError) as exc_info:
        CourseCanvasStore(StorageLayout(tmp_path / "workspaces")).write_draft(document)
    assert f"Duplicate {duplicate} ID" in str(exc_info.value.__cause__)


def test_legacy_publish_rejects_duplicate_checkpoint_ids_before_review(tmp_path: Path) -> None:
    store = CourseCanvasStore(StorageLayout(tmp_path / "workspaces"))
    document = _document()
    document.sections.append(
        CanvasSection(
            id="duplicate-gate-section",
            title="Duplicate gate",
            blocks=[
                CanvasBlock(
                    id="intro-check",
                    type="checkpoint",
                    text="Duplicate checkpoint.",
                )
            ],
        )
    )
    write_document_source(document, store.draft_path("design-course", "lecture-01"))

    with pytest.raises(InvalidCanvasDraftError) as exc_info:
        store.publish_draft(
            course_id="design-course",
            lecture_id="lecture-01",
            published_by="professor",
        )
    assert "Duplicate checkpoint ID" in str(exc_info.value.__cause__)


def test_update_preserves_exact_evidence_criterion_ids(tmp_path: Path) -> None:
    unknown_client = _client_with_draft(tmp_path / "unknown")
    unknown_review = unknown_client.get(_review_path(), headers=professor_headers()).json()
    unknown = _update_payload(unknown_review)
    unknown["gates"][0]["evidence_criteria"][0]["id"] = "unknown-criterion"

    duplicate_client = _client_with_draft(tmp_path / "duplicate")
    duplicate_review = duplicate_client.get(_review_path(), headers=professor_headers()).json()
    duplicate = _update_payload(duplicate_review)
    duplicate["gates"][0]["evidence_criteria"].append(
        dict(duplicate["gates"][0]["evidence_criteria"][0])
    )

    unknown_response = unknown_client.put(_review_path(), headers=professor_headers(), json=unknown)
    duplicate_response = duplicate_client.put(
        _review_path(), headers=professor_headers(), json=duplicate
    )

    assert unknown_response.status_code == 400
    assert duplicate_response.status_code == 400
