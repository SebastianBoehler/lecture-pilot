# Interleaved Slides Implementation Plan

> Historical 2026-06-18 plan. PDF slide interleaving has landed and TeX-only
> previews now use isolated Tectonic. Current behavior:
> [`course ingestion`](../../course-ingestion-pipeline.md) and
> [`LaTeX compilation`](../../latex-compilation.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show original professor slides inside generated lecture canvases by rendering source PDF pages to course assets and inserting representative slide image blocks into generated sections.

**Architecture:** Render PDF pages into PNG files under the course uploads tree, expose them through existing `/course-assets/...` URLs, and insert one representative original-slide `asset` block at the start of each generated canvas section. Reuse existing canvas asset rendering in the React app; no new frontend block type for v1.

---

## File Structure

- Create `apps/api/src/lecturepilot/pdf_slide_assets.py`: render PDF pages to stable PNG course assets and return `CanvasBlock` asset blocks.
- Create `apps/api/src/lecturepilot/course_slide_interleaving.py`: insert original-slide blocks into generated sections by page/frame match, then by even distribution.
- Modify `apps/api/src/lecturepilot/source_bundle_canvas.py`: include rendered slide assets in PDF source evidence.
- Modify `apps/api/src/lecturepilot/course_canvas_planner.py`: run interleaving after planning/enrichment and prompt for page/frame source refs.
- Add tests in `apps/api/tests/test_pdf_slide_assets.py` and `apps/api/tests/test_course_slide_interleaving.py`.
- Extend `apps/api/tests/test_source_bundle_canvas.py` and `apps/api/tests/test_course_canvas_planner.py`.

## Task 1: PDF Slide Asset Renderer

**Files:**

- Create: `apps/api/src/lecturepilot/pdf_slide_assets.py`
- Test: `apps/api/tests/test_pdf_slide_assets.py`

- [ ] **Step 1: Add failing renderer test**

Create `apps/api/tests/test_pdf_slide_assets.py`:

```python
from pathlib import Path

from lecturepilot.pdf_slide_assets import render_pdf_slide_blocks


def test_render_pdf_slide_blocks_creates_course_asset_pngs(tmp_path: Path) -> None:
    source_root = tmp_path / "uploads"
    source_root.mkdir()
    pdf_path = source_root / "lecture-01.pdf"
    _write_pdf(pdf_path, ["slide one", "slide two"])

    blocks = render_pdf_slide_blocks(
        pdf_path=pdf_path,
        source_root=source_root,
        course_id="demo-course",
        lecture_id="lecture-01",
        source_ref="lecture-01.pdf",
    )

    assert [block.id for block in blocks] == [
        "lecture-01-original-slide-001",
        "lecture-01-original-slide-002",
    ]
    assert blocks[0].asset_path == "generated-slides/lecture-01/lecture-01/slide-001.png"
    assert blocks[0].asset_url.endswith("generated-slides/lecture-01/lecture-01/slide-001.png")
    assert blocks[0].caption == "Original slide 1 from lecture-01.pdf"
    assert (source_root / blocks[0].asset_path).read_bytes().startswith(b"\x89PNG")


def _write_pdf(path: Path, labels: list[str]) -> None:
    import fitz

    document = fitz.open()
    for label in labels:
        page = document.new_page(width=160, height=90)
        page.insert_text((20, 45), label)
    document.save(path)
    document.close()
```

- [ ] **Step 2: Verify it fails**

Run: `pytest apps/api/tests/test_pdf_slide_assets.py -q`

- [ ] **Step 3: Implement renderer**

Create `apps/api/src/lecturepilot/pdf_slide_assets.py` with:

```python
from __future__ import annotations

from pathlib import Path

from lecturepilot.canvas_models import CanvasBlock
from lecturepilot.storage_layout import safe_id


MAX_RENDERED_SLIDES = 120


class PdfSlideAssetError(RuntimeError):
    """Raised when original slide images cannot be rendered."""


def render_pdf_slide_blocks(
    *,
    pdf_path: Path,
    source_root: Path,
    course_id: str,
    lecture_id: str,
    source_ref: str,
) -> list[CanvasBlock]:
    if pdf_path.suffix.lower() != ".pdf":
        raise PdfSlideAssetError("Only PDF source files can be rendered as slides.")
    fitz = _fitz()

    stem = safe_id(pdf_path.stem)
    slide_root = f"generated-slides/{safe_id(lecture_id)}/{stem}"
    output_dir = source_root / slide_root
    output_dir.mkdir(parents=True, exist_ok=True)
    document = fitz.open(pdf_path)
    try:
        return [
            _render_page(document, source_root, slide_root, course_id, lecture_id, source_ref, index)
            for index in range(min(len(document), MAX_RENDERED_SLIDES))
        ]
    finally:
        document.close()


def _render_page(document, source_root: Path, slide_root: str, course_id: str, lecture_id: str, source_ref: str, index: int) -> CanvasBlock:
    fitz = _fitz()
    number = index + 1
    asset_path = f"{slide_root}/slide-{number:03}.png"
    output_path = source_root / asset_path
    if not output_path.exists():
        pixmap = document.load_page(index).get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        pixmap.save(output_path)
    return CanvasBlock(
        id=f"{safe_id(lecture_id)}-original-slide-{number:03}",
        type="asset",
        asset_path=asset_path,
        asset_url=f"/course-assets/{course_id}/{lecture_id}/{asset_path}",
        caption=f"Original slide {number} from {source_ref}",
    )


def _fitz():
    try:
        import fitz
    except ImportError as exc:
        raise PdfSlideAssetError("PyMuPDF is required to render original slides.") from exc
    return fitz
```

- [ ] **Step 4: Verify renderer**

Run: `pytest apps/api/tests/test_pdf_slide_assets.py -q`

## Task 2: Add Slide Assets To PDF Source Evidence

**Files:**

- Modify: `apps/api/src/lecturepilot/source_bundle_canvas.py`
- Test: `apps/api/tests/test_source_bundle_canvas.py`

- [ ] **Step 1: Add failing source-bundle assertion**

Add `test_pdf_source_bundle_adds_original_slide_assets` to `apps/api/tests/test_source_bundle_canvas.py`: create a two-page `lecture-01.pdf`, call `import_source_bundle_canvas(...)`, collect blocks with `asset_path.startswith("generated-slides/")`, and assert captions `["Original slide 1 from lecture-01.pdf", "Original slide 2 from lecture-01.pdf"]`.

- [ ] **Step 2: Verify it fails**

Run: `pytest apps/api/tests/test_source_bundle_canvas.py::test_pdf_source_bundle_adds_original_slide_assets -q`

- [ ] **Step 3: Wire renderer into `_pdf_section`**

Import:

```python
from lecturepilot.pdf_slide_assets import PdfSlideAssetError, render_pdf_slide_blocks
```

In `_pdf_section`, after the existing whole-PDF asset block, add:

```python
try:
    blocks.extend(
        render_pdf_slide_blocks(
            pdf_path=path,
            source_root=source_root,
            course_id=course_id,
            lecture_id=lecture_id,
            source_ref=source_ref,
        )
    )
except PdfSlideAssetError as exc:
    raise SourceBundleCanvasError(str(exc)) from exc
```

- [ ] **Step 4: Verify source-bundle evidence**

Run: `pytest apps/api/tests/test_source_bundle_canvas.py::test_pdf_source_bundle_adds_original_slide_assets -q`

## Task 3: Interleave Slides Into Generated Sections

**Files:**

- Create: `apps/api/src/lecturepilot/course_slide_interleaving.py`
- Test: `apps/api/tests/test_course_slide_interleaving.py`

- [ ] **Step 1: Add interleaving tests**

Create `apps/api/tests/test_course_slide_interleaving.py` with tests proving `source_ref="lecture.pdf pages 2-3"` inserts `slide-002.png` first, sections without page refs receive first/last slides by even distribution, and original section blocks remain after the inserted slide.

- [ ] **Step 2: Verify tests fail**

Run: `pytest apps/api/tests/test_course_slide_interleaving.py -q`

- [ ] **Step 3: Implement interleaver**

Create `course_slide_interleaving.py` with `interleave_original_slides`, `_source_slides`, `_select_slide`, and `_page_numbers`. `_source_slides` returns `generated-slides/` assets whose caption starts with `Original slide `. `_page_numbers` parses `page 2`, `pages 2-3`, `frame 4`, and `frames 4-6`. `_select_slide` prefers first unused parsed page/frame; otherwise use `round(index * (len(slides) - 1) / max(1, total - 1))` and scan forward. `interleave_original_slides` prepends the selected slide unless the section already starts with a generated-slide asset.

- [ ] **Step 4: Verify interleaving**

Run: `pytest apps/api/tests/test_course_slide_interleaving.py -q`

## Task 4: Run Interleaving During Planning

**Files:**

- Modify: `apps/api/src/lecturepilot/course_canvas_planner.py`
- Test: `apps/api/tests/test_course_canvas_planner.py`

- [ ] **Step 1: Extend planner fixture**

Add two generated-slide source asset blocks to `_source_document()` and assert:

```python
assert document.sections[0].blocks[0].asset_path.startswith("generated-slides/")
assert document.sections[0].blocks[1].type == "paragraph"
```

- [ ] **Step 2: Verify planner test fails**

Run: `pytest apps/api/tests/test_course_canvas_planner.py::test_course_planner_restyles_source_evidence -q`

- [ ] **Step 3: Call interleaver**

Import `interleave_original_slides` in `course_canvas_planner.py`. In both normal and sectionwise paths, run:

```python
document = enrich_learning_document(_planned_document(payload, source_document))
document = interleave_original_slides(document, source_document)
validate_planned_document(document, source_document)
```

Use `sectionwise = interleave_original_slides(sectionwise, source_document)` in the fallback path.

- [ ] **Step 4: Update prompt/evidence**

In `_planner_messages`, add:

```python
"When original slide image assets are listed, use one as the recognition anchor for each section and cite the matching PDF page or frame in source_ref. "
```

In `_block_evidence`, emit `original slide` for generated-slide assets before the generic asset branch.

- [ ] **Step 5: Verify planner**

Run: `pytest apps/api/tests/test_course_canvas_planner.py::test_course_planner_restyles_source_evidence -q`

## Task 5: Verification And Commit

- [ ] **Step 1: Run focused tests**

Run:

```bash
pytest apps/api/tests/test_pdf_slide_assets.py apps/api/tests/test_course_slide_interleaving.py apps/api/tests/test_source_bundle_canvas.py apps/api/tests/test_course_canvas_planner.py -q
```

- [ ] **Step 2: Run full API tests**

Run: `pytest apps/api/tests -q`

- [ ] **Step 3: Run hygiene checks**

Run:

```bash
git diff --check
find apps/api/src apps/api/tests apps/web/src -type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.css' \) -print0 | xargs -0 wc -l | awk '$2 != "total" && $1 > 300 { print }'
```

- [ ] **Step 4: Commit**

Run:

```bash
git add apps/api/src/lecturepilot/pdf_slide_assets.py apps/api/src/lecturepilot/course_slide_interleaving.py apps/api/src/lecturepilot/source_bundle_canvas.py apps/api/src/lecturepilot/course_canvas_planner.py apps/api/tests/test_pdf_slide_assets.py apps/api/tests/test_course_slide_interleaving.py apps/api/tests/test_source_bundle_canvas.py apps/api/tests/test_course_canvas_planner.py
git commit -m "feat: interleave original slides in canvases"
```
