from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock, CanvasDocument, CanvasSection
from lecturepilot.latex_canvas_text import (
    clean_inline,
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
    if lecture_id != "lecture-03":
        return _read_frame_chunk_sections(frames, material_root, course_id, lecture_id)

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
    if items := read_items(body):
        blocks.append(CanvasBlock(id=f"{section_id}-list", type="list", items=items))
    for math_index, formula in enumerate(read_math_blocks(body), start=1):
        blocks.append(CanvasBlock(id=f"{section_id}-math-{math_index}", type="math", text=formula))
    for paragraph_index, paragraph in enumerate(paragraphs_from_latex(body), start=1):
        blocks.append(CanvasBlock(id=f"{section_id}-p-{paragraph_index}", type="paragraph", text=paragraph))
    for asset_index, asset in enumerate(read_assets(body, material_root=material_root), start=1):
        blocks.append(_asset_block(section_id, asset_index, asset, course_id, lecture_id))
    return blocks


def _read_frame_chunk_sections(
    frames: list[LatexFrame],
    material_root: Path,
    course_id: str,
    lecture_id: str,
) -> list[CanvasSection]:
    sections = []
    for frame in frames:
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
    return "frames " + ", ".join(str(frame.index) for frame in frames)


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
        title="Naive Bayes assumption",
        frame_slugs=("naive-bayes-classifiers",),
    ),
    CanvasGroup(
        id="naive-bayes-tradeoffs",
        title="Strengths, limits, and use cases",
        frame_slugs=("advantages-disadvantages-and-application-of-naive-bayes",),
    ),
    CanvasGroup(
        id="spam-filter-example",
        title="Spam filter example",
        frame_slugs=("naive-bayes-in-action-spam-filter",),
    ),
    CanvasGroup(
        id="text-preprocessing-pipeline",
        title="Text preprocessing pipeline",
        frame_slugs=("from-text-to-tokens", "identifying-top-words"),
    ),
    CanvasGroup(
        id="word-probability-estimates",
        title="Estimating word probabilities",
        frame_slugs=("computing-probabilities", "computing-probabilities-2"),
    ),
    CanvasGroup(
        id="laplace-smoothing",
        title="Laplace smoothing",
        frame_slugs=("laplace-smoothing",),
    ),
    CanvasGroup(
        id="classifying-new-email",
        title="Classifying a new email",
        frame_slugs=("classifying-a-new-email",),
    ),
    CanvasGroup(
        id="log-probability-scores",
        title="Log probability scores",
        frame_slugs=("using-log-probabilities",),
    ),
    CanvasGroup(
        id="decision-boundary-and-roc",
        title="Decision boundary and ROC",
        frame_slugs=(
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
CANVAS_IMPORT_VERSION = 10
_FRAME_RE = re.compile(
    r"\\begin\{frame}(?:\[[^]]*])?(?:\{(?P<title>[^{}]+)})?(?P<body>.*?)\\end\{frame}",
    re.DOTALL,
)
