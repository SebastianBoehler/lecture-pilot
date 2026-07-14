from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from lecturepilot.course_source_partition import COURSE_WIDE_RE
from lecturepilot.lecture_schedule import LECTURE_FILE_RE
from lecturepilot.source_bundle import SourceBundleFile


@dataclass(frozen=True)
class LectureSlideSource:
    primary_tex_path: str | None
    uploaded_pdf_path: str | None


def resolve_lecture_slide_source(
    *,
    files: list[SourceBundleFile],
    material_path: str | None,
    lecture_id: str,
    preferred_pdf_paths: set[str] | None = None,
) -> LectureSlideSource:
    if not material_path:
        return LectureSlideSource(None, None)
    scheduled = _find_file(files, material_path)
    if scheduled is None:
        return LectureSlideSource(None, None)
    if scheduled.kind == "pdf":
        return LectureSlideSource(None, scheduled.path)
    if scheduled.kind != "latex":
        return LectureSlideSource(None, None)

    primary = PurePosixPath(scheduled.path)
    candidates = [item for item in files if item.kind == "pdf"]
    exact = next(
        (
            item
            for item in candidates
            if _same_path(PurePosixPath(item.path), primary.with_suffix(".pdf"))
        ),
        None,
    )
    if exact:
        return LectureSlideSource(scheduled.path, exact.path)

    preferred = [item for item in candidates if item.path in (preferred_pdf_paths or set())]
    if len(preferred) == 1 and not COURSE_WIDE_RE.search(preferred[0].path):
        return LectureSlideSource(scheduled.path, preferred[0].path)

    lecture_number = _lecture_number(scheduled.path) or _lecture_number(lecture_id)
    numbered = [
        item
        for item in candidates
        if lecture_number is not None
        and _lecture_number(item.path) == lecture_number
        and (
            primary.parent == PurePosixPath(".")
            or PurePosixPath(item.path).parent == primary.parent
        )
        and not COURSE_WIDE_RE.search(item.path)
        and _looks_like_deck(PurePosixPath(item.path), primary)
    ]
    if numbered:
        selected = min(numbered, key=lambda item: _pdf_rank(item.path, primary))
        return LectureSlideSource(scheduled.path, selected.path)

    same_folder = [
        item
        for item in candidates
        if primary.parent != PurePosixPath(".")
        and PurePosixPath(item.path).parent == primary.parent
        and not COURSE_WIDE_RE.search(item.path)
        and _looks_like_deck(PurePosixPath(item.path), primary)
    ]
    selected = min(same_folder, key=lambda item: _pdf_rank(item.path, primary), default=None)
    return LectureSlideSource(scheduled.path, selected.path if selected else None)


def _find_file(files: list[SourceBundleFile], path: str) -> SourceBundleFile | None:
    folded = PurePosixPath(path).as_posix().casefold()
    return next((item for item in files if item.path.casefold() == folded), None)


def _same_path(left: PurePosixPath, right: PurePosixPath) -> bool:
    return left.as_posix().casefold() == right.as_posix().casefold()


def _lecture_number(value: str) -> int | None:
    match = LECTURE_FILE_RE.search(value)
    return int(match.group(1)) if match else None


def _pdf_rank(path: str, primary: PurePosixPath) -> tuple[int, int, int, str]:
    candidate = PurePosixPath(path)
    direct_sibling = candidate.parent == primary.parent
    deck_name = _looks_like_deck(candidate, primary)
    return (
        0 if direct_sibling else 1,
        0 if deck_name else 1,
        len(candidate.as_posix()),
        candidate.as_posix().casefold(),
    )


def _looks_like_deck(candidate: PurePosixPath, primary: PurePosixPath) -> bool:
    stem = candidate.stem.casefold()
    return stem == primary.stem.casefold() or any(
        marker in stem
        for marker in ("handout", "slides", "slide", "deck", "presentation", "notes", "skript")
    )
