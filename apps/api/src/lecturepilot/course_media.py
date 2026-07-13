from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.models import YoutubeSelectionInput, YoutubeSelectionResult, YoutubeVideoCandidate

COURSE_MEDIA_POOL_ID = "__course__"
MEDIA_SECTION_ID = "professor-selected-videos"


def add_youtube_selection(
    *,
    material_root: Path,
    course_id: str,
    lecture_id: str,
    selection: YoutubeSelectionInput,
    approved_by: str,
) -> YoutubeSelectionResult:
    path = _media_path(material_root, course_id=course_id, lecture_id=lecture_id)
    payload = _read_payload(path, course_id=course_id, lecture_id=lecture_id)
    block_id = f"youtube-{_safe_id(selection.video.video_id)}"
    next_entry = {
        "block_id": block_id,
        "section_id": selection.section_id,
        "approved_by": approved_by,
        "approved_at": datetime.now(UTC).isoformat(),
        "note": selection.note,
        "video": selection.video.model_dump(mode="json"),
    }
    entries = [entry for entry in payload["videos"] if entry.get("block_id") != block_id]
    payload["videos"] = [*entries, next_entry]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return YoutubeSelectionResult(
        course_id=course_id,
        lecture_id=lecture_id,
        section_id=selection.section_id,
        block_id=block_id,
        video=selection.video,
    )


def add_course_youtube_selection(
    *,
    material_root: Path,
    course_id: str,
    selection: YoutubeSelectionInput,
    approved_by: str,
) -> YoutubeSelectionResult:
    return add_youtube_selection(
        material_root=material_root,
        course_id=course_id,
        lecture_id=COURSE_MEDIA_POOL_ID,
        selection=selection.model_copy(update={"section_id": None}),
        approved_by=approved_by,
    )


def course_media_evidence(document: CanvasDocument, material_root: Path) -> CanvasDocument:
    videos = list_course_media(
        material_root=material_root,
        course_id=document.course_id,
        lecture_id=COURSE_MEDIA_POOL_ID,
    )
    blocks = [
        _evidence_video_block(YoutubeVideoCandidate.model_validate(entry["video"]))
        for entry in videos
    ]
    if not blocks:
        return document
    return document.model_copy(
        update={
            "sections": [
                *document.sections,
                CanvasSection(
                    id="professor-approved-video-evidence",
                    title="Professor approved video candidates",
                    source_ref="course media workspace",
                    blocks=blocks,
                ),
            ]
        }
    )


def apply_course_media(document: CanvasDocument, material_root: Path) -> CanvasDocument:
    sections = _collapse_media_sections(
        [section.model_copy(deep=True) for section in document.sections]
    )
    path = _media_path(material_root, course_id=document.course_id, lecture_id=document.lecture_id)
    if not path.exists():
        return document.model_copy(update={"sections": sections})
    payload = _read_payload(path, course_id=document.course_id, lecture_id=document.lecture_id)
    for entry in payload["videos"]:
        video = YoutubeVideoCandidate.model_validate(entry["video"])
        block = _video_block(video, block_id=str(entry["block_id"]))
        target = str(entry.get("section_id") or "")
        sections = _insert_video_block(sections, block=block, target_section_id=target)
    return document.model_copy(update={"sections": sections})


def _collapse_media_sections(sections: list[CanvasSection]) -> list[CanvasSection]:
    """Keep one canonical professor-media section and merge its unique blocks."""
    result: list[CanvasSection] = []
    media_index: int | None = None
    media_block_ids: set[str] = set()
    for section in sections:
        if section.id != MEDIA_SECTION_ID:
            result.append(section)
            continue
        if media_index is None:
            media_index = len(result)
            media_block_ids = {block.id for block in section.blocks}
            result.append(section)
            continue
        unique_blocks = [block for block in section.blocks if block.id not in media_block_ids]
        if not unique_blocks:
            continue
        media_block_ids.update(block.id for block in unique_blocks)
        canonical = result[media_index]
        result[media_index] = canonical.model_copy(
            update={"blocks": [*canonical.blocks, *unique_blocks]}
        )
    return result


def list_course_media(*, material_root: Path, course_id: str, lecture_id: str) -> list[dict]:
    path = _media_path(material_root, course_id=course_id, lecture_id=lecture_id)
    if not path.exists():
        return []
    return _read_payload(path, course_id=course_id, lecture_id=lecture_id)["videos"]


def remove_youtube_selection(
    *, material_root: Path, course_id: str, lecture_id: str, video_id: str
) -> int:
    path = _media_path(material_root, course_id=course_id, lecture_id=lecture_id)
    if not path.exists():
        return 0
    payload = _read_payload(path, course_id=course_id, lecture_id=lecture_id)
    block_id = f"youtube-{_safe_id(video_id)}"
    remaining = [entry for entry in payload["videos"] if entry.get("block_id") != block_id]
    if len(remaining) == len(payload["videos"]):
        return 0
    if not remaining:
        path.unlink()
        return 1
    payload["videos"] = remaining
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 1


def clear_course_media(*, material_root: Path, course_id: str) -> int:
    media_dir = material_root / "canvas" / "media"
    if not media_dir.exists():
        return 0
    prefix = f"{_safe_id(course_id)}-"
    deleted = 0
    for path in media_dir.glob(f"{prefix}*.json"):
        if not path.is_file():
            continue
        path.unlink()
        deleted += 1
    return deleted


def _insert_video_block(
    sections: list[CanvasSection],
    *,
    block: CanvasBlock,
    target_section_id: str,
) -> list[CanvasSection]:
    for index, section in enumerate(sections):
        if section.id != target_section_id:
            continue
        if any(existing.id == block.id for existing in section.blocks):
            return sections
        sections[index] = section.model_copy(update={"blocks": [*section.blocks, block]})
        return sections
    media_section = _media_section(block)
    for index, section in enumerate(sections):
        if section.id != media_section.id:
            continue
        if any(existing.id == block.id for existing in section.blocks):
            return sections
        sections[index] = section.model_copy(update={"blocks": [*section.blocks, block]})
        return sections
    return [*sections, media_section]


def _media_section(block: CanvasBlock) -> CanvasSection:
    return CanvasSection(
        id=MEDIA_SECTION_ID,
        title="Professor selected videos",
        source_ref="course media workspace",
        blocks=[block],
    )


def _video_block(video: YoutubeVideoCandidate, *, block_id: str) -> CanvasBlock:
    detail = f"{video.channel_title}"
    if video.duration.display:
        detail = f"{detail} · {video.duration.display}"
    return CanvasBlock(
        id=block_id,
        type="video",
        text=detail,
        asset_url=video.url,
        caption=video.title,
    )


def _evidence_video_block(video: YoutubeVideoCandidate) -> CanvasBlock:
    detail = f"{video.channel_title}"
    if video.duration.display:
        detail = f"{detail} · {video.duration.display}"
    if video.reason:
        detail = f"{detail} · {video.reason}"
    return CanvasBlock(
        id=f"course-video-{_safe_id(video.video_id)}",
        type="video",
        text=detail,
        asset_path=video.url,
        asset_url=video.url,
        caption=video.title,
    )


def _read_payload(path: Path, *, course_id: str, lecture_id: str) -> dict:
    if not path.exists():
        return {"course_id": course_id, "lecture_id": lecture_id, "videos": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("course_id") != course_id or payload.get("lecture_id") != lecture_id:
        raise ValueError("Course media payload does not match the requested lecture.")
    payload.setdefault("videos", [])
    return payload


def _media_path(material_root: Path, *, course_id: str, lecture_id: str) -> Path:
    return material_root / "canvas" / "media" / f"{_safe_id(course_id)}-{_safe_id(lecture_id)}.json"


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
    if not safe:
        raise ValueError("Course media id cannot be empty.")
    return safe[:120]
