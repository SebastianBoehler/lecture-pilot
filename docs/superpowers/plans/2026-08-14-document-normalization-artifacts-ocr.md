# Document Normalization, Artifacts, and OCR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Accept common academic Office and source-code formats from arbitrary folder trees, preserve faithful visual artifacts, and use selective efficient OCR only when native extraction is insufficient.

**Architecture:** Originals remain immutable under `source/uploads`. A no-secret document-converter service produces revision-keyed normalized manifests, Markdown evidence, rendered previews, and extracted assets under `source/normalized`; the API validates those outputs and converts them into existing canvas asset and table blocks. OCR is a page/region fallback chosen by deterministic triage, not the default parser for files with native structure.

**Tech Stack:** FastAPI/Pydantic, Docling structured conversion, LibreOffice headless rendering, PyMuPDF, PaddleOCR-VL candidate evaluation, React/TypeScript, Docker Compose.

## Global Constraints

- Never execute uploaded macros, scripts, formulas, notebook cells, or embedded actions.
- Keep originals authoritative and attach every normalized block to a source hash plus page, slide, sheet/range, or line locator.
- Reject encrypted, malformed, oversized, unsupported, or incomplete conversion outputs explicitly; never silently omit a file.
- Run conversion and OCR outside the API process with no secrets, read-only root filesystems, bounded temporary storage, CPU, memory, time, page count, pixels, and archive expansion.
- Keep source references in-app and never automatically fetch extracted URLs.
- Keep authored code files below the repository's 300-line soft limit.

---

### Task 1: Freeze the normalized-document contract

**Files:**

- Create: `apps/api/src/lecturepilot/source_normalization_models.py`
- Create: `apps/api/src/lecturepilot/source_normalization_store.py`
- Test: `apps/api/tests/test_source_normalization_store.py`
- Modify: `docs/course-ingestion-pipeline.md`

**Interfaces:**

- Consumes: immutable upload path, SHA-256, detected kind, and byte size.
- Produces: `NormalizedDocument`, `NormalizedBlock`, `SourceLocator`, and `load_normalized_document(root, sha256)`.
- [ ] **Step 1: Write failing model and store tests**

```python
def test_normalized_document_requires_revision_bound_locator(tmp_path: Path) -> None:
    payload = normalized_fixture(source_sha256="a" * 64)
    document = NormalizedDocument.model_validate(payload)
    assert document.blocks[0].locator.slide == 1
    assert document.source_sha256 == "a" * 64

def test_store_rejects_asset_path_outside_revision(tmp_path: Path) -> None:
    payload = normalized_fixture(asset_path="../stolen.png")
    with pytest.raises(SourceNormalizationError, match="inside the normalized revision"):
        write_normalized_fixture(tmp_path, payload)
        load_normalized_document(tmp_path, "a" * 64)
```

- [ ] **Step 2: Run the tests and verify the missing-contract failure**
      Run: `source .venv/bin/activate && pytest apps/api/tests/test_source_normalization_store.py -q`

- [ ] **Step 3: Add the strict models**

```python
class SourceLocator(BaseModel):
    page: int | None = Field(default=None, ge=1)
    slide: int | None = Field(default=None, ge=1)
    sheet: str | None = Field(default=None, max_length=120)
    cell_range: str | None = Field(default=None, max_length=80)
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    bbox: tuple[float, float, float, float] | None = None

class NormalizedCell(BaseModel):
    row: int = Field(ge=1)
    column: int = Field(ge=1)
    value: str | float | bool | None = None
    formula: str | None = Field(default=None, max_length=2_000)

class NormalizedBlock(BaseModel):
    kind: Literal["heading", "paragraph", "table", "formula", "code", "image", "link"]
    text: str | None = Field(default=None, max_length=60_000)
    asset_path: str | None = Field(default=None, max_length=500)
    url: AnyHttpUrl | None = None
    cells: list[NormalizedCell] = Field(default_factory=list, max_length=10_000)
    locator: SourceLocator
    extraction: Literal["native", "rendered", "ocr"]

class NormalizedDocument(BaseModel):
    schema_version: Literal[1]
    source_path: str
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_type: str
    blocks: list[NormalizedBlock] = Field(max_length=10_000)
    warnings: list[str] = Field(default_factory=list, max_length=100)
```

- [ ] **Step 4: Implement safe loading from `normalized/<sha256>/manifest.json`**
      Resolve every referenced asset through `WorkspaceFS`; require the manifest hash to match the requested upload revision and reject unknown schema versions or absolute/traversing paths.

- [ ] **Step 5: Run tests and document the four terminal file states**
      Run: `source .venv/bin/activate && pytest apps/api/tests/test_source_normalization_store.py -q`

Document: `usable evidence`, `preserved supporting media`, `excluded with reason`, and `unsupported/rejected`.

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/lecturepilot/source_normalization_models.py apps/api/src/lecturepilot/source_normalization_store.py apps/api/tests/test_source_normalization_store.py docs/course-ingestion-pipeline.md
git commit -m "feat(ingestion): define normalized source contract"
```

### Task 2: Build the isolated native-document converter

**Files:**

- Create: `apps/document-converter/pyproject.toml`
- Create: `apps/document-converter/Dockerfile`
- Create: `apps/document-converter/src/lecturepilot_converter/app.py`
- Create: `apps/document-converter/src/lecturepilot_converter/conversion.py`
- Create: `apps/document-converter/src/lecturepilot_converter/office_links.py`
- Create: `apps/document-converter/tests/test_conversion.py`
- Create: `apps/api/src/lecturepilot/document_converter_client.py`
- Test: `apps/api/tests/test_document_converter_client.py`
- Modify: `deploy/compose.yml`

**Interfaces:**

- Consumes: `POST /convert` multipart file plus `source_path` and `source_sha256`.
- Produces: a bounded archive containing `manifest.json`, `content.md`, `assets/`, and optional `rendered.pdf`.
- [ ] **Step 1: Add converter contract tests**

Create minimal DOCX, PPTX, and XLSX fixtures in test code. Assert that DOCX headings remain ordered, PPTX slide text/notes/hyperlinks retain slide numbers, and XLSX cells retain sheet/range plus formulas and cached values as separate fields.

- [ ] **Step 2: Run tests and verify unsupported-format failures**
      Run: `pytest apps/document-converter/tests/test_conversion.py -q`

- [ ] **Step 3: Implement conversion with an explicit allowlist**
      Allow `.docx`, `.pptx`, `.xlsx`, `.odt`, `.odp`, `.ods`, `.rtf`, `.html`, and `.epub`. Use Docling for structured blocks; read OOXML relationship files with `defusedxml` to retain hyperlinks and notes. Reject macro-enabled formats such as `.docm`, `.pptm`, and `.xlsm`.

- [ ] **Step 4: Render presentations and page-oriented documents**
      Invoke LibreOffice only inside the converter container with `--headless --safe-mode --convert-to pdf`, an empty temporary profile, no network, and a hard timeout. Return `rendered.pdf`; never treat its extracted text as a second authoritative source.

- [ ] **Step 5: Implement the API client and fail closed**

```python
class DocumentConverterClient:
    def convert(self, *, path: Path, source_path: str, sha256: str) -> NormalizedDocument: ...
```

Require HTTP 200, matching hash, valid manifest, bounded response bytes, and no unlisted archive members.

- [ ] **Step 6: Add the converter service boundary**

Add an internal-only Compose network, healthcheck, `read_only: true`, `cap_drop: [ALL]`, `no-new-privileges`, `pids_limit: 128`, `mem_limit: 3g`, `cpus: 2`, and bounded `/tmp`. Give the API only `LECTUREPILOT_DOCUMENT_CONVERTER_URL`.

- [ ] **Step 7: Run converter and API contract tests**

Run: `pytest apps/document-converter/tests apps/api/tests/test_document_converter_client.py -q`

- [ ] **Step 8: Commit**

```bash
git add apps/document-converter apps/api/src/lecturepilot/document_converter_client.py apps/api/tests/test_document_converter_client.py deploy/compose.yml
git commit -m "feat(ingestion): add isolated document converter"
```

### Task 3: Accept common academic formats and import modality-preserving artifacts

**Files:**

- Create: `apps/api/src/lecturepilot/course_material_formats.py`
- Modify: `apps/api/src/lecturepilot/workspace.py`
- Modify: `apps/api/src/lecturepilot/secure_upload.py`
- Modify: `apps/api/src/lecturepilot/source_bundle.py`
- Create: `apps/api/src/lecturepilot/source_bundle_normalized.py`
- Modify: `apps/api/src/lecturepilot/source_bundle_canvas.py`
- Test: `apps/api/tests/test_secure_upload.py`
- Test: `apps/api/tests/test_source_bundle.py`
- Test: `apps/api/tests/test_source_bundle_canvas.py`

**Interfaces:**

- Consumes: `NormalizedDocument` from Task 1 and `rendered.pdf` from Task 2.
- Produces: existing `CanvasSection` objects containing `asset`, `table`, `math`, `paragraph`, and `list` blocks with exact section-level locators.
- [ ] **Step 1: Write failing upload and import tests**

Assert that ZIP-based Office signatures are inspected through `[Content_Types].xml`, spoofed ZIPs fail, macro formats fail, same-named files in different folders stay distinct, PPTX produces slide assets plus text, and XLSX produces bounded table blocks with `sheet/range` source references.

- [ ] **Step 2: Run the narrow tests and verify failures**
      Run: `source .venv/bin/activate && pytest apps/api/tests/test_secure_upload.py apps/api/tests/test_source_bundle.py apps/api/tests/test_source_bundle_canvas.py -q`

- [ ] **Step 3: Extend the shared format policy**

Add Office/OpenDocument/HTML/EPUB suffixes and inert source-code suffixes (`.c`, `.h`, `.cpp`, `.hpp`, `.java`, `.kt`, `.js`, `.jsx`, `.ts`, `.tsx`, `.rs`, `.go`, `.r`, `.m`, `.swift`, `.sql`, `.sh`) to one registry imported by upload validation and bundle scanning. Treat source code as bounded UTF-8-compatible text and never execute it.

- [ ] **Step 4: Map normalized documents into canvas blocks**

PPTX/ODP: render slides from `rendered.pdf`, then interleave slide-scoped extracted text, notes, and safe HTTP(S) link annotations. XLSX/ODS: emit one section per bounded range with a Markdown table; record truncation and formulas explicitly. DOCX/ODT/RTF/HTML/EPUB: preserve headings, paragraphs, tables, formulas, images, and source order.

- [ ] **Step 5: Run the narrow and API suites**
      Run: `npm run verify:api`

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/lecturepilot apps/api/tests
git commit -m "feat(ingestion): import office and source-code materials"
```

### Task 4: Add selective OCR behind a measured quality gate

**Files:**

- Create: `benchmarks/document-ocr/README.md`
- Create: `scripts/benchmark_document_ocr.py`
- Create: `apps/document-converter/src/lecturepilot_converter/ocr_triage.py`
- Create: `apps/document-converter/src/lecturepilot_converter/ocr_client.py`
- Test: `apps/document-converter/tests/test_ocr_triage.py`
- Modify: `apps/document-converter/src/lecturepilot_converter/conversion.py`
- Modify: `deploy/compose.yml`

**Interfaces:**

- Consumes: rendered page image, native extracted text statistics, raster coverage, and encoding diagnostics.
- Produces: `OcrDecision(required, reasons)` and OCR blocks tagged `extraction="ocr"` with page/region locators.
- [ ] **Step 1: Create a private, gitignored evaluation corpus manifest**

Define six strata: German/English prose, lecture slides, formulas, source code, tables/charts, and degraded scans/handwriting. Store only hashes, category, expected text/formula/table assertions, and source permissions in the committed manifest; keep actual professor pages outside Git.

- [ ] **Step 2: Implement deterministic OCR triage tests**

```python
@pytest.mark.parametrize((chars, replacement_ratio, raster_ratio, required), [
    (0, 0.0, 1.0, True),
    (800, 0.0, 0.1, False),
    (120, 0.2, 0.8, True),
])
def test_ocr_decision(chars, replacement_ratio, raster_ratio, required):
    assert decide_ocr(chars, replacement_ratio, raster_ratio).required is required
```

- [ ] **Step 3: Benchmark PaddleOCR-VL, LightOnOCR-2, and DeepSeek-OCR2**

Measure character error rate, reading-order errors, formula exact/structure match, table TEDS, omissions, unsupported additions, p50/p95 seconds per page, peak RAM/VRAM, and output tokens. Select the lowest-cost candidate that passes every stratum's committed threshold; if none passes, leave OCR disabled and retain the evaluation report.

- [ ] **Step 4: Integrate the selected model as a separate worker**

Call OCR only for triaged pages/regions. Require structured output with bounding boxes, keep original renders, mark OCR-derived text, and reject output whose page identity or bounds do not match the request.

- [ ] **Step 5: Verify graceful unavailable-worker behavior**
      The conversion must finish with an explicit `OCR required but unavailable` warning and a preserved page artifact; it must not invent empty native text or block unrelated files.

- [ ] **Step 6: Run tests and commit**

Run: `pytest apps/document-converter/tests/test_ocr_triage.py -q`

```bash
git add benchmarks/document-ocr scripts/benchmark_document_ocr.py apps/document-converter deploy/compose.yml
git commit -m "feat(ingestion): add selective document OCR"
```

### Task 5: Expose conversion state and verify the complete professor-to-learner path

**Files:**

- Modify: `apps/api/src/lecturepilot/course_source_routing_models.py`
- Modify: `apps/api/src/lecturepilot/course_source_routing_routes.py`
- Test: `apps/api/tests/test_course_source_routing_api.py`
- Modify: `apps/web/src/ProfessorSourceRoutingEditor.tsx`
- Modify: `apps/web/src/CanvasMediaBlocks.tsx`
- Test: `apps/web/src/ProfessorSourceRoutingEditor.test.tsx`
- Test: `apps/web/src/App.canvas.test.tsx`
- Modify: `docs/course-ingestion-pipeline.md`
- Modify: `README.md`

**Interfaces:**

- Consumes: per-file normalization status, warnings, locators, and canvas artifacts.
- Produces: professor-visible status and learner-visible faithful artifacts without exposing storage paths.
- [ ] **Step 1: Write failing API/UI tests**

Assert visible statuses for converted, preserved, excluded, rejected, and OCR-needed files; assert a PPTX slide renders in-app; assert an XLSX table has its sheet/range source marker; assert extracted links are displayed but never fetched automatically.

- [ ] **Step 2: Implement status and artifact UI**

Keep rendered slides in the main canvas, use horizontally scrollable semantic tables with captions, and show extraction warnings in professor review. Do not add another side panel for primary learning content.

- [ ] **Step 3: Run broad verification**
      Run: `npm run verify:fast && npm run verify:api && npm run verify:web`

- [ ] **Step 4: Verify the real browser workflow**

At `http://127.0.0.1:5173`, upload a nested mixed-format folder, confirm every file has one terminal status, edit routing, generate a canvas, open rendered slides/tables, inspect source locators, and confirm zero browser console errors at desktop and narrow viewport widths.

- [ ] **Step 5: Verify deployment capacity before enabling OCR**

Record `docker stats --no-stream`, `docker system df`, host `df -h`, worker health, conversion latency, temporary-disk peak, and log warnings. Keep OCR on a separate worker if the production host cannot meet the selected model's measured envelope.

- [ ] **Step 6: Update documentation and commit**

```bash
git add apps/api apps/web README.md docs/course-ingestion-pipeline.md
git commit -m "feat: surface normalized course artifacts"
```

## Release Gate

- Every accepted file has exactly one visible terminal status.
- Native Office documents retain source structure and faithful previews.
- Tables/formulas/links have precise provenance; extracted links are never auto-fetched.
- OCR runs only where triage requires it and never in the API process.
- No uploaded code, macro, formula, notebook cell, or embedded action executes.
- API/web verification and the real mixed-folder browser workflow pass.
- Production capacity measurements justify the enabled converter/OCR configuration.
