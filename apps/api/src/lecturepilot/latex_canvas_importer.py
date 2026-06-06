from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.latex_canvas_text import (
    clean_inline,
    is_allowed_canvas_asset,
    is_skipped_frame_title,
    paragraphs_from_latex,
    read_assets,
    read_items,
    read_math_blocks,
    read_title,
    slug,
    strip_comments,
)


@dataclass(frozen=True)
class LatexFrame:
    index: int
    title: str
    body: str
    slug: str


@dataclass(frozen=True)
class CanvasGroup:
    id: str
    title: str
    frame_slugs: tuple[str, ...]


def import_latex_canvas(
    *,
    source_path: Path,
    material_root: Path,
    course_id: str,
    lecture_id: str,
    workspace_path: str,
) -> CanvasDocument:
    source = strip_comments(source_path.read_text(encoding="utf-8", errors="replace"))
    frames = _read_frames(source)
    return CanvasDocument(
        id=f"{course_id}-{lecture_id}",
        import_version=CANVAS_IMPORT_VERSION,
        course_id=course_id,
        lecture_id=lecture_id,
        title=read_title(source) or source_path.stem,
        source_kind="latex",
        source_ref=source_path.name,
        workspace_path=workspace_path,
        sections=_read_grouped_sections(frames, material_root, course_id, lecture_id),
    )


def _read_grouped_sections(
    frames: list[LatexFrame],
    material_root: Path,
    course_id: str,
    lecture_id: str,
) -> list[CanvasSection]:
    by_slug: dict[str, list[LatexFrame]] = {}
    for frame in frames:
        by_slug.setdefault(frame.slug, []).append(frame)

    sections = []
    for group in _LECTURE_03_GROUPS:
        group_frames = [frame for slug in group.frame_slugs for frame in by_slug.get(slug, [])]
        if not group_frames:
            continue
        sections.append(
            CanvasSection(
                id=group.id,
                title=group.title,
                source_ref=_source_ref(group_frames),
                blocks=_read_group_blocks(group.id, group_frames, material_root, course_id, lecture_id),
            )
        )
    return sections or _read_frame_chunk_sections(frames, material_root, course_id, lecture_id)


def _read_group_blocks(
    section_id: str,
    frames: list[LatexFrame],
    material_root: Path,
    course_id: str,
    lecture_id: str,
) -> list[CanvasBlock]:
    body = "\n".join(frame.body for frame in frames)
    blocks: list[CanvasBlock] = []
    for asset_index, asset in enumerate(read_assets(body, material_root=material_root)[:2], start=1):
        blocks.append(_asset_block(section_id, asset_index, asset, course_id, lecture_id))
    if items := read_items(body):
        blocks.append(CanvasBlock(id=f"{section_id}-list", type="list", items=items[:8]))
    for math_index, formula in enumerate(read_math_blocks(body)[:4], start=1):
        blocks.append(CanvasBlock(id=f"{section_id}-math-{math_index}", type="math", text=formula))
    for paragraph_index, paragraph in enumerate(paragraphs_from_latex(body)[:2], start=1):
        blocks.append(CanvasBlock(id=f"{section_id}-p-{paragraph_index}", type="paragraph", text=paragraph))
    return blocks


def _read_frame_chunk_sections(
    frames: list[LatexFrame],
    material_root: Path,
    course_id: str,
    lecture_id: str,
) -> list[CanvasSection]:
    sections = []
    for frame in frames[:12]:
        blocks = _read_group_blocks(frame.slug, [frame], material_root, course_id, lecture_id)
        if blocks:
            sections.append(
                CanvasSection(
                    id=frame.slug,
                    title=frame.title,
                    source_ref=f"frame {frame.index}",
                    blocks=blocks,
                )
            )
    return sections


def _read_frames(source: str) -> list[LatexFrame]:
    frames = []
    seen_ids: dict[str, int] = {}
    for index, match in enumerate(_FRAME_RE.finditer(source), start=1):
        title = clean_inline(match.group("title") or "")
        if not title or is_skipped_frame_title(title):
            continue
        frames.append(
            LatexFrame(
                index=index,
                title=title,
                body=match.group("body"),
                slug=_unique_slug(title, seen_ids),
            )
        )
    return frames


def _asset_block(
    section_id: str,
    asset_index: int,
    asset: str,
    course_id: str,
    lecture_id: str,
) -> CanvasBlock:
    return CanvasBlock(
        id=f"{section_id}-asset-{asset_index}",
        type="asset",
        asset_path=asset,
        asset_url=f"/course-assets/{course_id}/{lecture_id}/{asset}",
        caption=asset,
    )


def _source_ref(frames: list[LatexFrame]) -> str:
    return "frames " + ", ".join(str(frame.index) for frame in frames[:8])


def _unique_slug(title: str, seen_ids: dict[str, int]) -> str:
    base = slug(title)
    seen_ids[base] = seen_ids.get(base, 0) + 1
    return base if seen_ids[base] == 1 else f"{base}-{seen_ids[base]}"


_LECTURE_03_GROUPS = (
    CanvasGroup(
        id="bayesian-decision-theory-the-aim",
        title="Decision making under uncertainty",
        frame_slugs=("bayesian-decision-theory-the-aim", "introduction", "introduction-2"),
    ),
    CanvasGroup(
        id="bayes-formula",
        title="Bayes formula and conditional probability",
        frame_slugs=("refresher-conditional-probability", "bayes-formula", "bayes-formula-2", "bayes-formula-3"),
    ),
    CanvasGroup(
        id="bayes-rule-to-sum-up",
        title="Bayes rule for classification",
        frame_slugs=(
            "variables",
            "variables-2",
            "where-do-probabilities-come-from",
            "classification",
            "bayes-rule-prior",
            "bayes-rule-likelihood",
            "bayes-rule-evidence",
            "bayes-rule-to-sum-up",
            "making-decisions-with-conditional-probabilities",
            "making-decisions-with-conditional-probabilities-2",
            "summary",
        ),
    ),
    CanvasGroup(
        id="naive-bayes-classifiers",
        title="Naive Bayes spam filter",
        frame_slugs=(
            "naive-bayes-classifiers",
            "advantages-disadvantages-and-application-of-naive-bayes",
            "naive-bayes-in-action-spam-filter",
            "from-text-to-tokens",
            "identifying-top-words",
            "computing-probabilities",
            "laplace-smoothing",
            "computing-probabilities-2",
            "classifying-a-new-email",
            "using-log-probabilities",
            "adjusting-the-decision-boundary",
            "receiver-operating-characteristics-roc",
        ),
    ),
    CanvasGroup(
        id="losses-and-risks",
        title="Losses, risks, and reject decisions",
        frame_slugs=(
            "losses-and-risks",
            "losses-and-risks-2",
            "apply-to-zero-one-0-1-loss",
            "derivation-of-the-binary-decision-rule",
            "reject-option",
            "the-optimal-decision-rule-including-reject-option",
        ),
    ),
)
CANVAS_IMPORT_VERSION = 2
_FRAME_RE = re.compile(
    r"\\begin\{frame}(?:\[[^]]*])?(?:\{(?P<title>[^{}]+)})?(?P<body>.*?)\\end\{frame}",
    re.DOTALL,
)
