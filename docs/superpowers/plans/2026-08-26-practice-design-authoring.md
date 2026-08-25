# Practice Design Authoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require an exact professor-approved, source-grounded practice design before LecturePilot generates or publishes a lecture canvas.

**Architecture:** Add a course-owned `PracticeDesign` proposal/approval boundary after source routing, then pass an immutable approved snapshot through canvas planning, draft validation, learning-map construction, and publication. Keep learner runtime behavior unchanged in this slice; generated gates gain exact target bindings for the next SRL-runtime slice.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, filesystem-backed atomic stores, LiteLLM structured output, React 19, TypeScript, Vitest/Testing Library.

**Spec:** `docs/superpowers/specs/2026-08-26-practice-design-authoring.md`

## Global Constraints

- Professors own sources, outcomes, evidence, tasks, scaffolds, review timing, and approval.
- Canvas generation fails closed when the current practice design is missing, stale, or unapproved; do not add inferred or mock fallbacks.
- Existing published courses remain readable; unpublished legacy drafts must be regenerated.
- Keep every authored code/doc file at or below the repository's 300-line soft limit; split by responsibility before crossing it.
- Preserve private source material, exact tenant/course/lecture authority, atomic writes, and revision-bound publication.
- Add no dependency and no learner-runtime, confidence, AI-policy-enforcement, analytics, or human-handoff behavior in this slice.
- Add English and German UI copy and support light/dark mode through existing styles.

---

## File ownership map

- `course_practice_design_models.py`: strict public contracts and canonical revisions.
- `course_practice_design_store.py`: atomic proposal/edit/approval persistence and stale checks.
- `course_practice_design_validation.py`: source/task/hint deterministic validation.
- `course_practice_design_{client,prompt,planner}.py`: structured proposal generation only.
- `course_practice_design_routes.py`: professor-owned HTTP boundary.
- `course_practice_design_binding.py`: immutable draft/publication sidecar.
- Existing canvas generation/map/publication modules: consume and enforce the binding.
- `practiceDesign{Types,Api}.ts` and `useProfessorPracticeDesigns.ts`: web contract/state.
- `ProfessorPracticeDesignStep.tsx`: compact professor review UI.

### Task 1: Practice-design contracts and durable store

**Files:**

- Create: `apps/api/src/lecturepilot/course_practice_design_models.py`
- Create: `apps/api/src/lecturepilot/course_practice_design_validation.py`
- Create: `apps/api/src/lecturepilot/course_practice_design_store.py`
- Modify: `apps/api/src/lecturepilot/storage_layout.py`
- Test: `apps/api/tests/test_practice_design_store.py`

**Interfaces:**

- Produces `PracticeDesignProposal`, `PracticeDesign`, `PracticeDesignUpdate`, `PracticeDesignApprovalInput`, and `PracticeDesignStore.read/save_proposal/update/approve/require_approved`.
- `save_proposal(..., proposal, allowed_source_paths)`, `update(..., update, allowed_source_paths)`, and `require_approved(course_id, lecture_id, source_revision, design_revision=None) -> PracticeDesign` validate against the lecture's exact routed paths.

- [ ] Write model/store tests proving canonical revision stability, 1–8 targets, ID patterns, unknown source rejection, task variants must differ, ordered unique hints, stale/corrupt file rejection, edit-clears-approval, and atomic round-trip.

```python
class PracticeEvidenceCriterion(BaseModel):
    id: str
    description: str
    required: bool = True

class PracticeMisconception(BaseModel):
    id: str
    description: str
    diagnostic_cue: str

class PracticeHint(BaseModel):
    level: Literal["prompt", "cue", "faded_example", "worked_step"]
    content: str

class PracticeTarget(BaseModel):
    id: str
    title: str
    outcome: str
    baseline_task: str
    independent_exit_task: str
    delayed_transfer_task: str
    evidence_criteria: list[PracticeEvidenceCriterion]
    misconceptions: list[PracticeMisconception]
    hint_ladder: list[PracticeHint]
    review_after_days: int
    source_refs: list[str]

approved = store.approve(course_id="c", lecture_id="l", source_revision=SRC,
    design_revision=proposal.revision, approved_by="prof")
changed = store.update(course_id="c", lecture_id="l", current_source_revision=SRC,
    update=update(approved, objective="Changed outcome"))
assert changed.approval is None
with pytest.raises(PracticeDesignApprovalRequired):
    store.require_approved(course_id="c", lecture_id="l", source_revision=SRC)
```

- [ ] Run `source .venv/bin/activate && pytest apps/api/tests/test_practice_design_store.py -q`; expect import/contract failures.
- [ ] Implement strict models, digest excluding `revision`/`approval`, exact source-path validation, and an atomic `builder/practice-designs/<lecture>.json` store using `ensure_durable_directory` and `fsync_directory`.
- [ ] Re-run the narrow test; expect PASS.
- [ ] Commit: `git add apps/api/src/lecturepilot/{course_practice_design_models.py,course_practice_design_validation.py,course_practice_design_store.py,storage_layout.py} apps/api/tests/test_practice_design_store.py && git commit -m "feat(course-builder): add practice design contracts"`.

### Task 2: Source-grounded proposal planner and professor routes

**Files:**

- Create: `apps/api/src/lecturepilot/course_practice_design_client.py`
- Create: `apps/api/src/lecturepilot/course_practice_design_prompt.py`
- Create: `apps/api/src/lecturepilot/course_practice_design_planner.py`
- Create: `apps/api/src/lecturepilot/course_practice_design_routes.py`
- Modify: `apps/api/src/lecturepilot/course_canvas_routes.py`
- Modify: `apps/api/src/lecturepilot/app.py`
- Test: `apps/api/tests/test_practice_design_planner.py`
- Test: `apps/api/tests/test_practice_design_routes.py`

**Interfaces:**

- Consumes Task 1 contracts/store and existing `source_document(course_id, lecture_id)`.
- Produces `PracticeDesignPlanner.propose(source, source_revision) -> PracticeDesignProposal` and the four spec routes.

- [ ] Write planner tests asserting provider-native schema use, 3–6 requested targets without padding, exact supplied source paths, and provider errors without persisted partial output.
- [ ] Write route tests for owner-only GET/proposal/PUT/approve, `refresh=false` reuse, source-change `409`, stale edit `409`, invalid input `422`, and provider `502`/`503`.

```python
response = client.post("/admin/courses/c/lectures/l/practice-design/proposal", headers=owner)
revision = response.json()["revision"]
approved = client.post("/admin/courses/c/lectures/l/practice-design/approve", headers=owner,
    json={"source_revision": SRC, "practice_design_revision": revision})
assert approved.json()["approval"]["practice_design_revision"] == revision
```

- [ ] Run `source .venv/bin/activate && pytest apps/api/tests/test_practice_design_{planner,routes}.py -q`; expect missing modules/routes.
- [ ] Implement client/prompt/planner, initialize `app.state.practice_design_planner`, register routes beside canvas routes so they share the authoritative source resolver, and record provider usage/observability under `course_practice_design` without source text in logs.
- [ ] Re-run both tests; expect PASS.
- [ ] Commit: `git add apps/api/src/lecturepilot/course_practice_design_*.py apps/api/src/lecturepilot/{course_canvas_routes.py,app.py} apps/api/tests/test_practice_design_{planner,routes}.py && git commit -m "feat(course-builder): propose and approve practice designs"`.

### Task 3: Block generation and capture an immutable design snapshot

**Files:**

- Modify: `apps/api/src/lecturepilot/course_canvas_generation_ownership.py`
- Modify: `apps/api/src/lecturepilot/course_canvas_generation.py`
- Modify: `apps/api/src/lecturepilot/course_canvas_draft_routes.py`
- Modify: `apps/api/src/lecturepilot/course_canvas_repair_routes.py`
- Test: `apps/api/tests/test_practice_design_generation_preflight.py`

**Interfaces:**

- Consumes `PracticeDesignStore.require_approved`.
- Ownership records `practice_design_revision` and the generation/repair callback receives the frozen `PracticeDesign`; persist-time checks require the same approved revision.

- [ ] Write failures for missing/unapproved/stale design before model invocation, approved snapshot passed to generation and targeted repair, and source/design edits during either operation rejected.

```python
with pytest.raises(PracticeDesignApprovalRequired):
    await generate_course_canvas_draft(app, course_id="c", lecture_id="l", **generation_args)
assert fake_course_planner.calls == []
```

- [ ] Run `source .venv/bin/activate && pytest apps/api/tests/test_practice_design_generation_preflight.py -q`; expect generation to proceed incorrectly.
- [ ] Resolve source plus approved design under the course lock, return both with ownership, pass the frozen model through generation/repair callbacks, and repeat revision checks immediately before draft persistence.
- [ ] Re-run the narrow test plus `pytest apps/api/tests/test_course_canvas_generation_service.py apps/api/tests/test_canvas_generation_provenance.py -q`; expect PASS.
- [ ] Commit: `git add apps/api/src/lecturepilot/course_canvas_{generation_ownership.py,generation.py,draft_routes.py,repair_routes.py} apps/api/tests/test_practice_design_generation_preflight.py && git commit -m "feat(canvas): require approved practice design"`.

### Task 4: Make canvas planning and repairs implement the design

**Files:**

- Modify: `apps/api/src/lecturepilot/course_canvas_planner.py`
- Modify: `apps/api/src/lecturepilot/course_canvas_prompt.py`
- Modify: `apps/api/src/lecturepilot/course_canvas_section_planner.py`
- Modify: `apps/api/src/lecturepilot/course_canvas_section_prompt.py`
- Modify: `apps/api/src/lecturepilot/course_canvas_section_repair.py`
- Modify: `apps/api/src/lecturepilot/course_canvas_repair_prompt.py`
- Test: `apps/api/tests/test_practice_design_canvas_planner.py`

**Interfaces:**

- Changes `CourseCanvasPlanner.plan_canvas(source_document, *, practice_design, repair_context=None, output_language="en")` and every section/repair path to carry the same immutable design.
- `planner_messages(source_document, practice_design, *, output_language="en")` requires exact `practice-<target-id>` checkpoints and approved task content.

- [ ] Write tests that initial, section-by-section, automatic, and targeted repair prompts contain the design revision and applicable target contracts, and that returned drafts cannot omit or mutate canonical checkpoints.

```python
async def plan_canvas(self, source_document: CanvasDocument, *,
    practice_design: PracticeDesign, repair_context: str | None = None,
    output_language: str = "en") -> CanvasDocument: ...
```

- [ ] Run `source .venv/bin/activate && pytest apps/api/tests/test_practice_design_canvas_planner.py -q`; expect missing parameters/constraints.
- [ ] Thread the typed design through all planner/repair methods, scope section prompts to applicable targets without dropping the lecture-level contract, and enforce output coverage before a candidate can persist.
- [ ] Re-run the narrow test plus `pytest apps/api/tests/test_course_canvas_planner.py apps/api/tests/test_course_canvas_repair_preflight.py -q`; expect PASS.
- [ ] Commit: `git add apps/api/src/lecturepilot/course_canvas_{planner.py,prompt.py,section_planner.py,section_prompt.py,section_repair.py,repair_prompt.py} apps/api/tests/test_practice_design_canvas_planner.py && git commit -m "feat(canvas): generate from approved practice targets"`.

### Task 5: Bind targets into drafts, learning maps, and publication

**Files:**

- Create: `apps/api/src/lecturepilot/course_practice_design_binding.py`
- Modify: `apps/api/src/lecturepilot/learning_map.py`
- Modify: `apps/api/src/lecturepilot/course_canvas_store.py`
- Modify: `apps/api/src/lecturepilot/course_learning_design_models.py`
- Modify: `apps/api/src/lecturepilot/course_learning_design_store.py`
- Modify: `apps/api/src/lecturepilot/course_canvas_publication.py`
- Test: `apps/api/tests/test_practice_design_canvas_binding.py`
- Test: `apps/api/tests/test_practice_design_publication.py`

**Interfaces:**

- Produces `PracticeDesignBinding(source_revision, practice_design_revision)` at `practice-design-binding.json`.
- Changes `build_learning_map(document, practice_design)` so new gates require `practice_target_id`, exact baseline/evidence/transfer/review fields, and exact `practice-<target-id>` checkpoint coverage.
- New publication metadata carries `practice_design_revision`; legacy published metadata remains readable with `None`.

- [ ] Write tests rejecting missing/duplicate/unknown target checkpoints, altered task/criterion IDs, stale sidecars, post-generation approval without pre-approval, and publication mismatch; retain a legacy published-read regression.

```python
class PracticeDesignBinding(BaseModel):
    source_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    practice_design_revision: str = Field(pattern=r"^[a-f0-9]{64}$")
```

- [ ] Run `source .venv/bin/activate && pytest apps/api/tests/test_practice_design_{canvas_binding,publication}.py -q`; expect failures.
- [ ] Write/read the binding sidecar with the draft snapshot; build maps from the approved contract; add the practice revision to learning-design review/approval checks and publication metadata; fail unpublished legacy drafts closed.
- [ ] Re-run narrow tests plus `pytest apps/api/tests/test_learning_design_review_routes.py apps/api/tests/test_learning_design_versioning.py apps/api/tests/test_course_workspace_api.py -q`; expect PASS.
- [ ] Commit: `git add apps/api/src/lecturepilot/{course_practice_design_binding.py,learning_map.py,course_canvas_store.py,course_learning_design_models.py,course_learning_design_store.py,course_canvas_publication.py} apps/api/tests/test_practice_design_{canvas_binding,publication}.py && git commit -m "feat(canvas): bind practice design revisions"`.

### Task 6: Web contracts and multi-lecture state

**Files:**

- Create: `apps/web/src/practiceDesignTypes.ts`
- Create: `apps/web/src/practiceDesignApi.ts`
- Create: `apps/web/src/useProfessorPracticeDesigns.ts`
- Test: `apps/web/src/practiceDesignApi.test.ts`
- Test: `apps/web/src/useProfessorPracticeDesigns.test.tsx`

**Interfaces:**

- Produces `PracticeDesign`, `PracticeDesignUpdate`, `get/propose/update/approvePracticeDesign`, and a hook keyed by lecture ID.
- Hook exposes `{designs, pendingLectureId, error, loadAll, propose, save, approve, reset}` and `allApproved(lectureIds)`.

- [ ] Write API URL/body/error tests and hook tests for single/full-course load, `404` as not-yet-proposed, save clearing approval, approval, stale `409`, and reset after source change.

```ts
export async function approvePracticeDesign(input: {
  courseId: string;
  lectureId: string;
  design: PracticeDesign;
  session: LoginSession;
}): Promise<PracticeDesign>;
```

- [ ] Run `npm test --workspace apps/web -- practiceDesignApi.test.ts useProfessorPracticeDesigns.test.tsx`; expect missing modules.
- [ ] Implement strict TypeScript types, authenticated fetch functions, and immutable per-lecture hook updates; surface all non-404 failures.
- [ ] Re-run the two tests; expect PASS.
- [ ] Commit: `git add apps/web/src/practiceDesign{Types,Api}.ts apps/web/src/useProfessorPracticeDesigns.ts apps/web/src/{practiceDesignApi,useProfessorPracticeDesigns}.test.* && git commit -m "feat(web): add practice design state"`.

### Task 7: Professor review step and builder blocking

**Files:**

- Create: `apps/web/src/ProfessorPracticeDesignStep.tsx`
- Create: `apps/web/src/ProfessorPracticeTargetEditor.tsx`
- Create: `apps/web/src/professor-practice-design.css`
- Modify: `apps/web/src/ProfessorBuilderStepper.tsx`
- Modify: `apps/web/src/ProfessorCourseBuilder.tsx`
- Modify: `apps/web/src/useProfessorCourseBuilder.ts`
- Modify: `apps/web/src/i18nMessages.en.ts`
- Modify: `apps/web/src/i18nMessages.de.ts`
- Modify: `apps/web/src/professor.css`
- Test: `apps/web/src/ProfessorPracticeDesignStep.test.tsx`
- Test: `apps/web/src/ProfessorCourseBuilder.practiceDesign.test.tsx`

**Interfaces:**

- Consumes Task 6 hook.
- Adds `BuilderStep = ... | "design"`; `designReady` requires every target lecture's current approval. Media remains reviewable, but generation requires `designReady && routingReady && reviewReady`.

- [ ] Write UI tests for source → design → media → generate order, compact target summaries, collapsed details, editable content with stable IDs, save-before-approve, all-lectures approval, stale messaging, and disabled generation.

```tsx
{
  builder.activeStep === "design" ? (
    <ProfessorPracticeDesignStep {...builder.practiceDesignStep} />
  ) : null;
}
```

- [ ] Run `npm test --workspace apps/web -- ProfessorPracticeDesignStep.test.tsx ProfessorCourseBuilder.practiceDesign.test.tsx`; expect missing step/components.
- [ ] Implement the focused components, builder reset/restore integration, seven-step numbering, accessible labels/status, and EN/DE copy; do not present approval as factual paragraph validation.
- [ ] Re-run narrow tests plus `npm test --workspace apps/web -- ProfessorCourseBuilder.test.tsx ProfessorBuilderStepper.test.ts`; expect PASS.
- [ ] Commit: `git add apps/web/src/{ProfessorPracticeDesignStep.tsx,ProfessorPracticeTargetEditor.tsx,ProfessorBuilderStepper.tsx,ProfessorCourseBuilder.tsx,useProfessorCourseBuilder.ts,i18nMessages.en.ts,i18nMessages.de.ts,professor-practice-design.css,professor.css,ProfessorPracticeDesignStep.test.tsx,ProfessorCourseBuilder.practiceDesign.test.tsx} && git commit -m "feat(course-builder): review practice design before generation"`.

### Task 8: Documentation and end-to-end verification

**Files:**

- Modify: `AGENTS.md`
- Modify: `docs/workspaces.md`

**Interfaces:** Documents `builder/practice-designs/<lecture>.json`, draft binding, builder order, invalidation, and the next-slice boundary.

- [ ] Update storage/workflow docs without claiming learner efficacy or runtime AI-policy enforcement.

```text
builder/practice-designs/<lecture-id>.json
canvas-drafts/lectures/<lecture-id>/latest/practice-design-binding.json
```

- [ ] Run `npm run verify:fast`, then `npm run verify:api`, then `npm run verify:web`; expect PASS for each.
- [ ] Run the repository file-size guard from `AGENTS.md`; expect no new file above 300 lines.
- [ ] Start API/web with documented local commands and verify source confirmation → proposal → edit → approve → generate, then change sources and confirm generation blocks; inspect console/network errors. If provider/compiler credentials are unavailable, record the exact missing live check instead of substituting mock evidence.
- [ ] Commit: `git add AGENTS.md docs/workspaces.md && git commit -m "docs: document practice design workflow"`.
