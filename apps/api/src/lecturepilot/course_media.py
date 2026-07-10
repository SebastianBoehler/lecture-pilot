from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.models import YoutubeSelectionInput, YoutubeSelectionResult, YoutubeVideoCandidate

COURSE_MEDIA_POOL_ID = "__course__"


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
    blocks = [_evidence_video_block(YoutubeVideoCandidate.model_validate(entry["video"])) for entry in videos]
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
    path = _media_path(material_root, course_id=document.course_id, lecture_id=document.lecture_id)
    if not path.exists():
        return document
    payload = _read_payload(path, course_id=document.course_id, lecture_id=document.lecture_id)
    sections = [section.model_copy(deep=True) for section in document.sections]
    for entry in payload["videos"]:
        video = YoutubeVideoCandidate.model_validate(entry["video"])
        block = _video_block(video, block_id=str(entry["block_id"]))
        target = str(entry.get("section_id") or "")
        sections = _insert_video_block(sections, block=block, target_section_id=target)
    return document.model_copy(update={"sections": sections})


def list_course_media(*, material_root: Path, course_id: str, lecture_id: str) -> list[dict]:
    path = _media_path(material_root, course_id=course_id, lecture_id=lecture_id)
    if not path.exists():
        return []
    return _read_payload(path, course_id=course_id, lecture_id=lecture_id)["videos"]


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
    if sections and sections[-1].id == media_section.id:
        if any(existing.id == block.id for existing in sections[-1].blocks):
            return sections
        sections[-1] = sections[-1].model_copy(update={"blocks": [*sections[-1].blocks, block]})
        return sections
    return [*sections, media_section]


def _media_section(block: CanvasBlock) -> CanvasSection:
    return CanvasSection(
        id="professor-selected-videos",
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
