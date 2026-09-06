# Learning Evidence Flow Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement
> independent tasks with focused review; execute coupled integration locally.

**Goal:** Deliver an explicit learning loop with credible attempt provenance,
reviewed task variants, shared German/English teaching and efficient course reads.

**Architecture:** Preserve professor intent and canonical publication authority.
Extend the existing coaching state machine and typed publication artifacts.
Shared teaching stays separate from learner attempts and model-selected prose.

**Tech Stack:** FastAPI, Pydantic, Pydantic AI, React, TypeScript, existing files/Postgres.

**Spec:** `docs/superpowers/specs/2026-09-06-learning-evidence-flow.md`

## Global Constraints

- New code files stay below 300 lines.
- Legacy approved design and published learning-map hashes remain readable.
- Hidden assessments never enter canvas teaching authoring prompts.
- No arbitrary code execution or unreviewed runtime-generated assessments.
- No production deployment or automatic approval migration.

## Task 1: Reviewed variants and coaching evidence

Files: practice-target/task-bank models, practice-design evidence/schema/reviewer,
learning-map contracts, coaching state/transitions/assessment, learner lesson state,
new typed support action and focused API tests. Keep frontend changes for Task 2.

Interfaces: lesson state exposes pending stage/task identity, assistance content,
focus-required flag and evidence per goal. A support-request endpoint binds exact
pending gate/revision/task before changing support exposure. Task 2 consumes this.

- [ ] Reproduce supported-task reuse in a focused coaching test.
- [ ] Add typed source-backed parallel variants and bounded numerical checks to
      practice targets; include nonempty banks in content hashes while preserving old
      hashes for absent fields. New native proposals produce banks.
- [ ] Compile variants to the private published learning map; validate source,
      rubric and hidden-task separation. Select fresh tasks by persisted exposure.
- [ ] Record help before release, preserve correct task-specific assessment input,
      and expose supported/independent/delayed evidence without learner prose in events.
- [ ] Verify stale request, double submit, bank exhaustion, goal/source revision,
      old hashes and exact next-check ownership. Run relevant broader API tests.

Acceptance example:

```python
assert after_help.pending_check.stage == "exit_support"
assert fresh.pending_check.task_id != helped_task_id
assert helped_task_id in fresh.exposed_task_ids
```

## Task 2: Focused canvas learning loop

Files: new focused-attempt/learning-evidence React components and hooks;
LessonWorkspace, CanvasLearningBlocks, learnerLessonStateTypes; EN/DE messages.

Interfaces: consumes Task 1 state/support API; keeps assessment submissions through
existing typed checkpoint action. Hide assistance surfaces during focused work.

- [ ] Write a UI regression showing a pending independent check hides relevant
      content and help cannot reveal it before the server acknowledges exposure.
- [ ] Show goal, task stage, missing evidence and support inline in the canvas.
- [ ] Preserve current task and empty answer on reload/revision change; distinguish
      supported, independent and delayed evidence with no generic mastery badge.
- [ ] Test help failure, stale response, reload, keyboard access and changed task.

Acceptance example:

```tsx
expect(screen.queryByText(workedExample)).not.toBeInTheDocument();
await user.click(screen.getByRole("button", { name: "Get help" }));
expect(requestSupport).toHaveBeenCalled();
```

## Task 3: Reviewed German/English explanation variants

Files: new canvas-language-variant models/store/provider/routes; registration;
new professor variant review and learner selector components/API/hooks/tests.

Interfaces: canonical course/lecture published snapshot -> exact translated
teaching document + base publication and variant digest. Learner output retains
canonical assessment identity and language. No changes to Task 1 task content.

- [ ] Test translation rejects changed checkpoint, formula, source and block IDs.
- [ ] Generate exact-schema teaching replacements through the existing native
      provider; persist private variant draft bound to canonical publication.
- [ ] Add manager preview/publish actions with exact draft/base digest CAS and
      authenticated learner read of current published variants only.
- [ ] Add professor controls and learner language selector showing assessment
      language explicitly; preserve private learner overlays and error state.
- [ ] Test stale publication, auth/role/cross-course checks and EN/DE UI behavior.

Acceptance example:

```python
assert translated_checkpoint == canonical_checkpoint
with pytest.raises(ValueError):
    publish_variant(stale_base_revision)
```

## Task 4: Professor implementation changes

Files: typed deterministic design-change summary helper/API and professor review UI.

- [ ] Compare saved implementation with archived previous snapshot by stable target
      identity; show changed task fields and protected goal changes separately.
- [ ] Display recorded repair reason only when persisted by actual repair work.
- [ ] Test exact diff, no previous history, unchanged content and source boundary.

Acceptance example:

```python
assert changes[0].target_id == "precision"
assert changes[0].fields == ["baseline_task"]
```

## Task 5: Profile and reuse published reads

Files: published snapshot reader and separate bounded cache; focused invalidation
and isolation tests; private benchmark script/output.

- [ ] Measure repeated current snapshot reads on a private published rehearsal.
- [ ] If parsing is material, reuse compiled validated snapshots keyed by the
      full relevant file identity plus canonical publication; return independent copies.
- [ ] Reject modified/deleted/tampered artifacts and preserve authorization at
      callers; avoid caching user overlays or privilege decisions.
- [ ] Repeat same benchmark; record timings, limits and concurrent invalidation.

Acceptance example:

```python
second.document.title = "private mutation"
assert read_snapshot().document.title == original_title
```

## Task 6: Integration and review

- [ ] Update architecture, evaluation and ownership docs to actual final contracts.
- [ ] Run narrow regressions, API/web suites, production build, lint/format/links.
- [ ] Independent code review of coupled authority, exposure and publication paths.
- [ ] Rehearse a real professor course and student help/fresh task/reload; review
      and publish a language variant locally; inspect dark/light and narrow layout.
- [ ] Record actual provider/runtime evidence, measured performance and limitations.
