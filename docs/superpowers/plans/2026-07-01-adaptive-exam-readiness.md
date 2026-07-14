# Adaptive Exam Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` for parallel execution, or
> `superpowers:executing-plans` for sequential execution. Update checkboxes as
> each step lands.

**Goal:** turn the existing exam readiness check into a persisted,
source-backed adaptive revision loop for LecturePilot without adding a
free-roaming agent.

**Working assumption:** the next meeting with Prof. Martius needs a credible
AIS-for-universities slice: students get cross-lecture diagnosis and targeted
revision tasks; professors get source-grounded, privacy-preserving signals
later. V1 optimizes the student loop first.

**Success check:** after a learner submits a readiness check, the backend stores
the attempt under the learner course workspace, returns a typed revision plan,
and the UI renders source-linked tasks with guidance intensity. No model
provider call is required.

## Research Constraints

- AIS shows the right product shape: adaptive paths, tutor, teacher dashboard,
  editor, and learning analytics. LecturePilot should copy the loop, not the
  whole platform: course-source diagnosis first, dashboard later.
- Sibley/Lachner adaptive-teaching work points to iterative formative
  assessment and delayed learning, so store attempts over time instead of only
  showing an immediate local score.
- Deininger/Colling learning-analytics work argues for theory-aligned trace
  indicators, not raw time tracking. Persist task status, first try correctness,
  attempt index, retry/revisit, and source ids.
- Lachner/Wagner feedback work argues against "more guidance by default." Use
  guidance levels: high performers get sparse challenge tasks; weak attempts get
  scaffolded tasks and concise feedback after an answer.
- Bear/Rudzewitz/Meurers task and feedback systems favor task-specific prompts,
  rubrics, and feedback hypotheses over open chat. Every revision item needs a
  goal, expected evidence, source ref, and next action.
- Glandorf/Meurers pedagogical-control work supports explicit constraints.
  Generated or selected tasks should carry concept/rubric constraints rather
  than relying on a broad prompt.
- Boos/Eder/Lachner utility-value findings make motivational scaffolds
  conditional. Do not inject "why this matters" copy unless the learner profile
  or repeated noncompletion warrants it.
- Holz/Meurers pedagogical-agent work supports trust cues, not persona bloat.
  Use professor-approved source refs and original slide/canvas anchors as the
  trust signal.

## Harness Boundary

No new general-purpose tools are needed for V1.

The readiness loop exposes one typed application action:
`record_readiness_attempt`. It records answers/results and returns a revision
plan. It is a convenience over learner course progress, not permission for the
agent to freely write progress files.

For a later tutor turn on one revision task, context should include only:
course id, lecture id, section id, question prompt, learner answer, MC correct
answer when applicable, rubric items, source ref, task status, and the relevant
published canvas excerpt.

Allowed tutor tools for that turn:

- `read`: read the selected published canvas excerpt and learner progress.
- `focus`: jump the canvas to the weak section.
- `highlight`: mark the relevant block or phrase.
- `record_gate`: record the follow-up evidence check.
- `write`: only for generated learner notes under `canvas/student/*.md`.

Explicitly not in this feature:

- free `find`/`grep` over all course sources;
- raw professor source reads;
- model-scored open answers;
- motivational/persona customization;
- image generation;
- raw time-on-task analytics;
- professor dashboard redesign.

## File Plan

- Create `apps/api/src/lecturepilot/exam_revision_plan.py`.
- Create `apps/api/src/lecturepilot/readiness_progress.py`.
- Create `apps/api/src/lecturepilot/readiness_analytics.py`.
- Modify `apps/api/src/lecturepilot/exam_readiness_routes.py`.
- Modify `apps/api/src/lecturepilot/analytics_routes.py`.
- Modify `apps/web/src/types.ts`.
- Modify `apps/web/src/api.ts`.
- Modify and split `apps/web/src/ExamReadinessPanel.tsx`.
- Modify `AGENTS.md`.

## Task 1: Pure Revision Planner

- [x] Add Pydantic models:
      `ExamReadinessAnswer`, `ExamReadinessAttemptInput`,
      `ExamReadinessQuestionResult`, `ExamRevisionTask`,
      `ExamReadinessAttemptResult`.
- [x] Implement `build_exam_revision_plan(check, answers, previous_attempts=())`
      as a pure function.
- [x] Score MC questions deterministically.
- [x] Preserve open-ended answers as `needs_rubric_review`; do not model-score.
- [x] Build one revision task per wrong MC and one rubric-review task per open
      answer.
- [x] Add `guidance_level`:
      `challenge` for strong MC score, `standard` for mixed score,
      `scaffolded` for weak score or repeated failure.
- [x] Include `source_ref`, `lecture_id`, `section_id`, `rubric`,
      `expected_evidence`, and `next_action` on every task.
- [x] Test wrong MC, open answer preservation, guidance levels, missing answer
      validation, and stable task ids.
- [x] Run `pytest apps/api/tests/test_exam_revision_plan.py -q`.

## Task 2: Persist Attempts In Learner Progress

- [x] Store progress at
      `StorageLayout.user_course_root(user_id, course_id) / "progress.json"`.
- [x] Keep schema small: `attempts`, `active_tasks`, `updated_at`.
- [x] Persist theory-aligned fields only: `attempt_id`, `question_id`,
      `task_id`, `lecture_id`, `section_id`, `answer_kind`, `correct`,
      `first_try`, `attempt_index`, `status`, `created_at`.
- [x] Add `POST /courses/{course_id}/exam-readiness/attempts`.
- [x] Reuse the same published-canvas and learner-access checks as the GET
      route.
- [x] Return `ExamReadinessAttemptResult`.
- [x] Test authenticated learner success, rejected unauthenticated request,
      user isolation, and no write to official course source.
- [x] Run
      `pytest apps/api/tests/test_exam_readiness.py apps/api/tests/test_readiness_progress.py -q`.

## Task 3: UI Submission And Revision Tasks

- [x] Add TypeScript types for answers, attempt result, revision tasks, and
      guidance level.
- [x] Add `submitExamReadinessAttempt(courseId, answers, session)`.
- [x] Replace local-only `gradeCheck` result with backend submission.
- [x] Render task cards grouped by lecture with source ref, guidance level,
      expected evidence, and a review button.
- [x] Keep open answers visible with rubric-review status, not fake correctness.
- [x] Show backend errors directly.
- [x] Preserve the current "open lecture" navigation path.
- [x] Keep `ExamReadinessPanel.tsx` under 300 lines by extracting task/result
      components.
- [x] Run `npm run test --workspace apps/web -- Dashboard.test.tsx`.

## Task 4: Minimal Professor Signal

- [x] Add a course-level summary helper over learner progress files:
      attempts count, unique learners, task completion counts, weak section ids.
- [x] Do not expose learner free text, chat transcripts, or raw identifiers.
- [x] Add `GET /admin/courses/{course_id}/exam-readiness/summary`.
- [x] Defer web professor UI unless `ProfessorCoursePerformance.tsx` is split
      first.
- [x] Run `pytest apps/api/tests/test_readiness_analytics.py -q`.

## Task 5: AGENTS.md Harness Documentation

- [x] Add `record_readiness_attempt` as a typed readiness action.
- [x] Document readiness context: selected task, source excerpt, rubric, and
      learner course progress summary only.
- [x] Document feedback policy: after attempt, concise, source-backed, no
      keyword auto-pass, guidance intensity depends on readiness.
- [x] Document analytics policy: theory-aligned event fields, no raw time as a
      primary signal, no raw learner text in professor aggregate.
- [x] Document deferrals: model scoring, broad source search, image generation,
      professor dashboard redesign.

## Task 6: Final Verification

- [x] Run `pytest apps/api/tests/test_exam_revision_plan.py apps/api/tests/test_exam_readiness.py apps/api/tests/test_readiness_progress.py -q`.
- [x] Run `pytest apps/api/tests/test_readiness_analytics.py -q`.
- [x] Run `npm run test --workspace apps/web -- Dashboard.test.tsx`.
- [x] Run `npm run build --workspace apps/web`.
- [x] Run `git diff --check`.
- [x] Run the file-size guard from `AGENTS.md`.

## Review Notes

Recommended implementation order was Tasks 1-3 first. Task 4 was added only as
a backend aggregate to avoid growing the oversized professor UI file.

Deferred deliberately: live university login, provider/model scoring, new
agent personas, broad search tools, image generation, and professor UI redesign.

Verification note: the repo-wide file-size guard still reports pre-existing
oversized files. The changed files remain under the 300-line guideline.

Source links used for this plan:

- AIS: https://ais.schule/
- Sibley et al. adaptive teaching: https://publikationen.bibliothek.kit.edu/1000180752
- Sibley et al. feasibility: https://hsbiblio.uni-tuebingen.de/xmlui/handle/10900/159468
- Deininger et al. theory-informed analytics: https://doi.org/10.1037/edu0000906
- Colling et al. sequence analysis: https://doi.org/10.1080/01443410.2025.2599786
- Lachner et al. non-interactive teaching: https://link.springer.com/article/10.1007/s10648-025-10060-0
- Wagner et al. feedback and instruction: https://doi.org/10.1016/j.learninstruc.2023.101844
- Bear et al. task-based conversational agent: https://doi.org/10.1016/j.system.2024.103460
- Rudzewitz et al. task feedback: https://aclanthology.org/W18-0513/
- Glandorf and Meurers pedagogical control: https://aclanthology.org/2024.bea-1.24/
- Boos, Eder, and Lachner utility moderation: https://doi.org/10.1016/j.caeo.2025.100324
- Holz et al. pedagogical-agent preferences: https://link.springer.com/chapter/10.1007/978-3-031-93567-1_6
