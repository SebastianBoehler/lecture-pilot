# Private Practice Exam Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an enrolled learner generate one immutable, source-grounded practice exam, optionally enriched by privately retained PPI protocols, then complete it online or download the same questions as a print-ready PDF.

**Architecture:** Store PPI imports and exams below the authenticated learner's hashed course workspace. Generate one private typed exam through bounded structured model calls, return only a public projection, render the browser and trusted LaTeX PDF from that projection, and keep Exam Readiness unchanged.

**Tech Stack:** FastAPI, Pydantic 2, `tue-api-wrapper==0.3.0`, PyMuPDF, LiteLLM structured JSON, isolated Tectonic compiler, React 19, TypeScript, Vitest, pytest.

## Global Constraints

- Use only currently unlocked published canvases as factual authority.
- PPI protocols may influence exam pattern but never provide the sole factual anchor or be reproduced verbatim.
- Keep PPI credentials in request memory only; never persist or log credentials, cookies, protocol text, prompts, rubrics, or backend learner answers.
- Spend a PPI token only after a fresh state check and `confirm_token_spend=true`.
- Retain validated PPI sources privately and indefinitely until explicit source, course-workspace, or account deletion.
- Generate 20–30 questions, default 25, and a default 90-minute duration.
- No grading, submission, solutions, scan ingestion, or readiness-progress integration.
- Keep every new code file below 300 lines; do not add mock/fallback product behavior.

---

### Task 1: Canonical exam and learner storage contracts

**Files:**

- Create: `apps/api/src/lecturepilot/practice_exam_models.py`
- Create: `apps/api/src/lecturepilot/practice_exam_store.py`
- Modify: `apps/api/src/lecturepilot/storage_layout.py`
- Test: `apps/api/tests/test_practice_exam_store.py`

**Interfaces:**

- Produces: `PracticeExam`, `PracticeExamPublic`, `PracticeExamQuestion`, `PracticeExamGenerationInput`, `public_practice_exam(exam)`, and `PracticeExamStore` methods `write`, `read`, `list`, `delete`.

- [ ] **Step 1: Write failing model and isolation tests**

```python
def test_public_exam_hides_authoring_data():
    public = public_practice_exam(_exam(answer_index=1, rubric=["Uses invariance."]))
    assert "answer_index" not in public.model_dump_json()
    assert "rubric" not in public.model_dump_json()

def test_store_isolates_users(tmp_path):
    store = PracticeExamStore(StorageLayout(tmp_path))
    store.write(user_id="a", course_id="ml", exam=_exam())
    with pytest.raises(FileNotFoundError):
        store.read(user_id="b", course_id="ml", exam_id=_exam().id)
```

- [ ] **Step 2: Run `pytest apps/api/tests/test_practice_exam_store.py -q` and verify missing imports fail.**
- [ ] **Step 3: Implement strict Pydantic models, public projection, safe path builders, atomic JSON writes, deterministic newest-first listing, and exact deletion.**
- [ ] **Step 4: Rerun the test and `python -m ruff check` for these files; expect PASS.**
- [ ] **Step 5: Commit `feat(exams): add private practice exam storage`.**

### Task 2: Safe private PPI import

**Files:**

- Create: `apps/api/src/lecturepilot/ppi_exam_source_models.py`
- Create: `apps/api/src/lecturepilot/ppi_exam_source_archive.py`
- Create: `apps/api/src/lecturepilot/ppi_exam_source_store.py`
- Create: `apps/api/src/lecturepilot/ppi_exam_source_service.py`
- Create: `apps/api/src/lecturepilot/ppi_exam_source_routes.py`
- Modify: `apps/api/src/lecturepilot/app.py`
- Test: `apps/api/tests/test_ppi_exam_source_archive.py`
- Test: `apps/api/tests/test_ppi_exam_source_api.py`

**Interfaces:**

- Consumes: `StorageLayout.user_course_root` and `tue_api_wrapper.PpiClient`.
- Produces: `PpiExamSourceManifest`, `PpiCatalogResponse`, `PpiImportInput`, `PpiExamSourceStore`, and `register_ppi_exam_source_routes(...)`.

- [ ] **Step 1: Write failing archive tests for valid PDF/TXT import and traversal, absolute path, hidden path, symlink, duplicate, suffix, file-count, compressed-size, expanded-size, and malformed-PDF rejection.**

```python
def test_archive_rejects_traversal(tmp_path):
    archive = _zip({"../stolen.txt": b"question"})
    with pytest.raises(PpiArchiveError, match="unsafe path"):
        normalize_ppi_archive(archive, output_root=tmp_path)
```

- [ ] **Step 2: Run `pytest apps/api/tests/test_ppi_exam_source_archive.py -q`; expect missing module failure.**
- [ ] **Step 3: Implement bounded ZIP inspection, PyMuPDF validation/text extraction, hashes, staging-directory publication, and cleanup on every failure.**
- [ ] **Step 4: Write failing API tests for cached listing, invalid credentials, already-borrowed download without borrow, unconfirmed borrow rejection, confirmed one-token borrow, stale state recheck, no tokens, deletion, CSRF, and learner isolation.**
- [ ] **Step 5: Run `pytest apps/api/tests/test_ppi_exam_source_api.py -q`; expect 404/missing route failures.**
- [ ] **Step 6: Implement short-lived client creation with `SecretStr`, exact catalog DTOs, fresh state checks, explicit token confirmation, metadata-only events, atomic store writes, routes, and app registration.**
- [ ] **Step 7: Run both PPI test files and ruff; expect PASS.**
- [ ] **Step 8: Commit `feat(exams): import private PPI protocol sources`.**

### Task 3: Source-grounded exam planner and validator

**Files:**

- Create: `apps/api/src/lecturepilot/practice_exam_schema.py`
- Create: `apps/api/src/lecturepilot/practice_exam_prompt.py`
- Create: `apps/api/src/lecturepilot/practice_exam_validation.py`
- Create: `apps/api/src/lecturepilot/practice_exam_planner.py`
- Test: `apps/api/tests/test_practice_exam_planner.py`
- Test: `apps/api/tests/test_practice_exam_validation.py`

**Interfaces:**

- Consumes: published `CanvasDocument` values and normalized `PpiExamSourceManifest` content.
- Produces: `practice_exam_response_format()`, `PracticeExamPlanner.plan(...) -> PracticeExam`, and `validate_practice_exam(exam, authoritative_source_ids, question_count)`.

- [ ] **Step 1: Write failing validator tests for 20–30 count, unique prompts/IDs, MC option and answer integrity, points, official source anchors, PPI-only anchors, and leaked protocol excerpts.**

```python
def test_rejects_ppi_only_question():
    exam = _exam(questions=[_question(source_ids=[], ppi_pattern_ids=["ppi-42"])])
    with pytest.raises(PracticeExamValidationError, match="course source"):
        validate_practice_exam(exam, authoritative_source_ids={"lecture-01:risk"}, question_count=20)
```

- [ ] **Step 2: Run validation tests; expect missing module failure.**
- [ ] **Step 3: Implement strict provider JSON schema, bounded blueprint/question prompts, original-question instruction, authoritative source IDs, and deterministic validation.**
- [ ] **Step 4: Write planner tests with a fake structured client for valid generation, provider failure, malformed payload, duplicate repair, unresolved repair, and no unlocked source coverage.**
- [ ] **Step 5: Implement `LiteLLMPracticeExamClient` with native `response_format`, usage recording, provider capability checks, bounded repair attempts, and no fallback.**
- [ ] **Step 6: Run planner/validation tests and ruff; expect PASS.**
- [ ] **Step 7: Commit `feat(exams): generate source-grounded practice exams`.**

### Task 4: Recoverable learner generation API

**Files:**

- Create: `apps/api/src/lecturepilot/practice_exam_generation_jobs.py`
- Create: `apps/api/src/lecturepilot/practice_exam_generation.py`
- Create: `apps/api/src/lecturepilot/practice_exam_routes.py`
- Modify: `apps/api/src/lecturepilot/app.py`
- Test: `apps/api/tests/test_practice_exam_api.py`
- Test: `apps/api/tests/test_practice_exam_generation_jobs.py`

**Interfaces:**

- Consumes: `PracticeExamPlanner`, `PracticeExamStore`, `PpiExamSourceStore`, `lecture_views_for_context`, and canvas reads.
- Produces: idempotent generation/list/read/delete/status routes and `PracticeExamGenerationStatus`.

- [ ] **Step 1: Write failing job-store tests for begin, replay, stale-lease retry, completion, failure, user isolation, and terminal-record pruning below the learner course root.**
- [ ] **Step 2: Implement the atomic job store with hashed request keys and generated operation IDs; rerun tests.**
- [ ] **Step 3: Write failing route tests for enrollment, professor denial, unlocked-only canvases, source ownership, idempotent replay, provider error, public projection, list/read/delete, CSRF, and metadata-only observability.**

```python
response = client.post(
    "/courses/demo/practice-exam-generations",
    headers={**student_headers("a"), "Idempotency-Key": "exam-generation-0001"},
    json={"question_count": 25, "duration_minutes": 90, "ppi_source_ids": []},
)
assert response.status_code == 200
assert "answer_index" not in response.text
```

- [ ] **Step 4: Implement route authorization, unlocked canvas resolution, exact selected-source failure, model-usage scope, generation persistence, safe errors, status recovery, and app state/registration.**
- [ ] **Step 5: Run both generation API tests plus existing exam-readiness tests; expect PASS.**
- [ ] **Step 6: Commit `feat(exams): expose recoverable practice exam API`.**

### Task 5: Trusted print-ready PDF rendering

**Files:**

- Create: `apps/api/src/lecturepilot/practice_exam_latex.py`
- Create: `apps/api/src/lecturepilot/practice_exam_pdf.py`
- Modify: `apps/api/src/lecturepilot/latex_compilation_client.py`
- Modify: `apps/api/src/lecturepilot/practice_exam_routes.py`
- Test: `apps/api/tests/test_practice_exam_pdf.py`
- Test: `apps/api/tests/test_practice_exam_api.py`

**Interfaces:**

- Consumes: `PracticeExamPublic`.
- Produces: `render_practice_exam_tex(exam) -> str`, `compile_latex_document(...) -> Path`, and authenticated `/pdf` response.

- [ ] **Step 1: Write failing TeX tests covering escaping of `\\`, `{}`, `%`, `$`, `&`, `_`, `#`, `^`, `~`, stable ordering, MC boxes, open-answer space, headers, points, and absence of answers/rubrics/provenance.**
- [ ] **Step 2: Implement a fixed template and escaping function; rerun the TeX tests.**
- [ ] **Step 3: Write failing compiler/cache tests for valid PDF, content fingerprint cache, compiler unavailable, invalid PDF, auth isolation, and retry without exam regeneration.**
- [ ] **Step 4: Extract a bounded generic `compile_latex_document` path from the existing client without weakening archive/hash/PDF validation, then cache `exam.pdf` atomically.**
- [ ] **Step 5: Run PDF, compiler-client, and compiler-service tests; expect PASS.**
- [ ] **Step 6: Commit `feat(exams): render practice exams as PDF`.**

### Task 6: Learner web flow and online exam

**Files:**

- Create: `apps/web/src/practiceExamTypes.ts`
- Create: `apps/web/src/practiceExamApi.ts`
- Create: `apps/web/src/practiceExamDraft.ts`
- Create: `apps/web/src/PracticeExamPanel.tsx`
- Create: `apps/web/src/PracticeExamSetup.tsx`
- Create: `apps/web/src/PpiExamSourcePicker.tsx`
- Create: `apps/web/src/PracticeExamView.tsx`
- Create: `apps/web/src/practice-exam.css`
- Modify: `apps/web/src/Dashboard.tsx`
- Modify: `apps/web/src/main.tsx`
- Modify: `apps/web/src/i18nMessages.en.ts`
- Modify: `apps/web/src/i18nMessages.de.ts`
- Test: `apps/web/src/PracticeExamPanel.test.tsx`
- Test: `apps/web/src/practiceExamDraft.test.ts`

**Interfaces:**

- Consumes: generation, PPI source, exam, deletion, and PDF endpoints.
- Produces: dashboard `PracticeExamPanel`, setup/import dialog, exam library, focused online exam, tab-scoped response drafts, and authenticated PDF download.

- [ ] **Step 1: Write failing API/state tests for request DTOs, idempotency headers, authenticated PDF blobs, tab draft save/read/clear, and account/course/exam key separation.**
- [ ] **Step 2: Implement typed API/state helpers; run tests and expect PASS.**
- [ ] **Step 3: Write failing component tests for the empty state, cached reuse without credentials, PPI-specific credential copy, already-borrowed import, exact token confirmation, 25/90 defaults, generation recovery, online inputs, PDF error, delete confirmations, and English/German strings.**
- [ ] **Step 4: Implement focused components, verb-first actions, accessible dialogs/fields/status regions, dashboard placement beside readiness, and responsive light/dark styles.**
- [ ] **Step 5: Run `npm run test --workspace apps/web -- PracticeExamPanel.test.tsx practiceExamDraft.test.ts` and `npm run build --workspace apps/web`; expect PASS.**
- [ ] **Step 6: Commit `feat(web): add private practice exam flow`.**

### Task 7: Lifecycle, documentation, and end-to-end verification

**Files:**

- Modify: `apps/api/src/lecturepilot/learner_workspace_reset.py`
- Modify: `apps/api/tests/test_learner_workspace_reset.py`
- Modify: `AGENTS.md`
- Modify: `docs/workspaces.md`
- Modify: `docs/tenancy-security.md`
- Modify: `apps/web/src/productChangelog.json`

**Interfaces:**

- Consumes: completed storage/routes/UI.
- Produces: reset/account lifecycle coverage, current workspace documentation, and verified release-facing behavior.

- [ ] **Step 1: Write a failing reset test proving private PPI sources, generation records, exams, and PDFs are removed without touching shared course sources; keep browser-draft cleanup covered by `practiceExamDraft.test.ts`.**
- [ ] **Step 2: Implement reset/lifecycle deletion and update workspace, authorization, agent-boundary, and changelog documentation.**
- [ ] **Step 3: Run focused API/web tests, `npm run verify:api`, `npm run verify:web`, `git diff --check`, and the AGENTS.md file-size guard; fix only feature-related failures.**
- [ ] **Step 4: Start the real API, web app, PostgreSQL, and compiler; verify generation without PPI, cached-source selection, online completion, valid PDF pages, responsive layout, keyboard flow, and zero browser console errors. Record that a live PPI borrow/download remains unverified if credentials are unavailable.**
- [ ] **Step 5: Commit `docs(exams): document private practice exam workflow`.**
- [ ] **Step 6: Review the complete diff for secrets, raw protocols, private workspace files, mock data, oversized new files, and accidental Exam Readiness changes; leave the worktree clean.**
