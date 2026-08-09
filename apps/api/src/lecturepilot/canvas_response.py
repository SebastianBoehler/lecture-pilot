from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from lecturepilot.canvas_models import CanvasDocument


class PublishedCanvasView(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    document: CanvasDocument
    publication_version: int = Field(strict=True, ge=1)
    learning_map_revision: str = Field(
        strict=True,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )


def published_canvas_payload(
    document: CanvasDocument,
    *,
    publication_version: int,
    learning_map_revision: str,
    include_answers: bool,
) -> dict:
    view = PublishedCanvasView(
        document=document,
        publication_version=publication_version,
        learning_map_revision=learning_map_revision,
    )
    payload = view.model_dump(exclude={"document": {"workspace_path"}})
    if not include_answers:
        for section in payload["document"].get("sections", []):
            for block in section.get("blocks", []):
                block.pop("answer_index", None)
    return payload
