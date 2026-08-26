# Practice Design Pedagogy Hardening Plan

> **For agentic workers:** Use test-driven development and the repository's
> subagent-driven development workflow. Every behavior change starts with a
> focused failing regression.

**Goal:** Make the professor-approved practice design a source-verifiable,
non-vacuous teaching contract that the learner runtime actually administers.

**Authority:** The professor remains authoritative. The model proposes and
checks; deterministic code validates structure and exact source anchors;
unresolved semantic concerns remain visible and block approval when critical.

**Evidence boundary:** This work implements research-aligned mechanisms. It
does not claim that LecturePilot improves learning; that requires a prospective
study measuring delayed unaided transfer.

## Global constraints

- Optimize for delayed, unaided performance; never treat assisted completion,
  engagement, speed, or confidence as mastery.
- Keep the source, design, review, generation, and learner-gate revisions exact.
- Require professor-visible evidence for generated content; no path-only claim
  of source grounding and no unrelated-section fallback.
- The server, not the tutor model, chooses the approved next assessment and
  scaffold. The model may phrase interaction around the frozen content but may
  not invent replacement tasks or hints.
- Fail closed on empty evidence, missing anchors, stale authority, unsupported
  fields, or provider review failure. Add no mock or production fallback.
- Keep files at or below the repository's 300-line soft limit and preserve EN,
  DE, light mode, and dark mode for changed UI.

## Task 1: Strengthen the proposal contract and planner instruction

**Files:** `course_practice_design_models.py`,
`course_practice_design_prompt.py`, `course_practice_design_planner.py`, focused
planner/store tests and shared fixtures.

- [x] Require at least one required evidence criterion per target.
- [x] Add an explicit target invariant plus controlled surface-change
      descriptions for exit and transfer tasks.
- [x] Add a professor-editable planning context: learner level, prerequisites,
      time budget, allowed aids, and assessment conditions. The model prefills it;
      missing source support becomes an explicit insufficiency, not invention.
- [x] Define diagnostic attempt, unaided exit, delayed changed-form transfer,
      atomic evidence, misconception boundaries, and each approved hint level in
      the provider instruction and response-schema descriptions.
- [x] Keep target count source-driven rather than implying that 3-6 targets or
      a model-selected delay is scientifically optimal.
- [x] Preserve canonical revisions and stable nested identities.

## Task 2: Add field-level source anchors and semantic review

**Files:** new small evidence/review models as needed,
`course_practice_design_validation.py`, planner/client/routes/store, focused
validation and route tests.

- [x] Require an exact source path and verbatim bounded excerpt for the outcome,
      invariant, each task, each required criterion, each misconception, and every
      content-bearing hint.
- [x] Validate excerpts against the exact routed source revision supplied to the
      planner; reject missing or unrelated anchors before persistence.
- [x] Run a second provider-native structured critic over the proposal and
      source packet for entailment, objective-task alignment, task equivalence,
      answer leakage, difficulty drift, transfer novelty, rubric sufficiency, and
      target/source coverage.
- [x] Persist the revision-bound review. Critical issues block approval;
      noncritical issues and supporting excerpts remain visible to the professor.
- [x] Provider failure fails closed and never persists a partially reviewed
      proposal.

## Task 3: Enforce exact source placement and carry the teaching contract

**Files:** canvas practice contract/validation, section planning, learning-map
models/building, focused canvas-binding tests.

- [x] Remove first-section fallback assignment. Every target checkpoint must be
      placed in a section carrying one of its validated source anchors.
- [x] Reject a checkpoint whose section source does not match the approved
      target evidence.
- [x] Carry the invariant, independent exit, misconceptions, and approved hint
      ladder into the revision-bound learning-map gate and active tutor context.
- [x] Preserve exact baseline, criteria, transfer prompt, delay, and nested IDs.

## Task 4: Administer the approved scaffold and independent exit

**Files:** coaching state/check binding/progress/orchestration, scaffold policy,
model context, analytics integrity, focused coaching tests.

- [x] The server selects only the next approved hint level/content; the tutor
      cannot invent a substitute ladder.
- [x] Record the exact approved hint exposed and bind assistance classification
      to the next attempt.
- [x] A supported baseline pass must issue the approved independent-exit task
      with assistance `none` before delayed review is scheduled.
- [x] Only the unaided exit pass schedules delayed transfer. Exit failure
      returns to bounded approved support without being classified as mastery.
- [x] Treat only `none` as independent evidence; a process prompt remains an
      assisted attempt in analytics.

## Task 5: Expose evidence and quality controls in professor review

**Files:** practice-design TypeScript contracts/API/hook, professor design
components/styles/i18n, focused UI tests.

- [x] Continue to prefill every field with the agent proposal.
- [x] Present planning context, invariant, controlled task changes, and source
      excerpts beside the fields they support.
- [x] Show critic findings by severity and explain why approval is blocked.
- [x] Keep the primary action review/approve; advanced edits remain targeted and
      stable-ID preserving.
- [x] Preserve compact responsive behavior without eyebrow-style labels,
      decorative cards, gradients, or marketing composition.

## Task 6: Add a reproducible pedagogical quality benchmark

**Files:** benchmark script, frozen synthetic/public fixtures, evaluator models,
tests, and concise documentation.

- [x] Score the real provider and production schema across multiple disciplines
      for source faithfulness, measurable outcomes, task answerability, exit
      equivalence, transfer invariance/novelty, rubric sufficiency, hint leakage,
      misconception plausibility, and source coverage.
- [x] Retain per-dimension scores, reviewer disagreement, and failure examples;
      do not collapse readiness into one opaque score.
- [x] Keep the benchmark opt-in and non-flaky; deterministic contract tests stay
      in CI, while provider quality informs prompt/model selection.
- [x] Document that only prospective unaided-exit and delayed-transfer outcomes
      can support a learning-effect claim.

## Verification

Run focused red/green tests per task, then:

```bash
npm run verify:fast
npm run verify:api
npm run verify:web
git diff --check
find apps/api/src apps/api/tests apps/web/src -type f \
  \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.css' \) \
  -print0 | xargs -0 wc -l | awk '$2 != "total" && $1 > 300 { print }'
```
