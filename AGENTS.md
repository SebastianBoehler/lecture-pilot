# AGENTS.md

This file is for coding agents working on LecturePilot. Keep it current when
setup, tests, workspace layout, or module ownership changes.

## Project Overview

LecturePilot is a lightweight, text-first university course tutor. The product
is not a generic chatbot: the web app, backend policy layer, course workspace,
and agent harness cooperate to teach only authorized, already-unlocked lecture
material.

Core flow:

```txt
student login -> enrolled courses -> past lectures only -> attendance mode
-> filesystem-backed canvas -> guided tutor turn -> persisted learner overlay
```

The frontend never talks directly to model providers. Provider routing belongs
behind the backend agent harness contract.

Optional tutor dictation runs Whistle locally in the browser for English/German.
It edits the message draft; only Send submits text through the existing backend.
Audio never enters provider routing. See `docs/browser-dictation.md` for module
ownership, pinned build assets and microphone/CSP requirements.

## Setup Commands

```bash
npm install
python3 -m venv .venv
source .venv/bin/activate
pip install -e "apps/api[test,agent]"
cp .env.local.example .env.local
```

Add Uni Tuebingen wrapper support only when working on live university login.

```bash
pip install -e "apps/api[tuebingen]"
# or, against a local wrapper checkout:
pip install -e ../tue-api-wrapper/package
```

## Dev Servers

```bash
source .venv/bin/activate
# In another terminal, run the isolated compiler container documented in README.md.
export LECTUREPILOT_LATEX_COMPILER_URL=http://127.0.0.1:8081
uvicorn lecturepilot.app:app --app-dir apps/api/src --reload
npm run dev --workspace apps/web
```

Open `http://127.0.0.1:5173`. Use **Preview local demo** for local UI and
agent-flow checks without sending real credentials.
The development demo student discovers accessible local courses for its
development enrollment headers through `localDemoCourses.ts`. Authenticated
university sessions retain their backend-provided enrollments.

## Agent Storage Image

The agent should be seeded with this logical filesystem image. Production keeps
database authority in Postgres and files on the persisted `/app/storage` volume.

```txt
.lecturepilot/
  users/<user-key>/
    profile.json
    memories/{global.md,preferences.json,memory-trace.jsonl}
    courses/<course-id>/
      {progress.json,last-visit.json}
      exam-sources/ppi/<ppi-lecture-id>/{manifest.json,source.zip,normalized/}
      practice-exam-generations/<request-key-hash>.json
      practice-exams/<exam-id>/{exam.json,exam.pdf,solutions.pdf,attempts/<uuid>.json}
      memories/{course.md,memory-trace.jsonl}
      lectures/<lecture-id>/
        {attendance.json,gates.json,tutor-state.json,assessment-audit.jsonl}
        annotations/<name>.json
        canvas/{student/*.md,components/*.yaml,student-assets/*}
  courses/<tenant-id>/<course-id>/
    course.json
    source/{uploads/,normalized/,source-index.json}
    canvas/lectures/<lecture-id>/{index.md,sections/*.md,assets/}
    canvas-drafts/lectures/<lecture-id>/latest/{...,practice-design-binding.json}
    builder/{generations/,practice-designs/<lecture-id>.json,repairs/,source-manifests/,source-routing.json,updates/}
    builder/implementation-jobs/<lecture-id>/<identity>/{draft.json,session.json}
  .storage-migrations.json
```

Official source material belongs to `courses/<tenant>/<course>/source`.
Professor-approved learning documents belong to
`courses/<tenant>/<course>/canvas`. Cross-course teaching preferences belong to
`users/<user-key>/memories`. Lecture-specific attendance, gates, progress,
generated notes, and generated images belong under the user's course/lecture
workspace.

The agent uses a small set of low-level typed tools over this image. Default
tutor gets `pwd`, `ls`, `read`, `write`, `edit`, `focus`, `highlight`,
`generate_image`, and consent-checked `remember`.
Evidence-heavy turns add `find` and `grep`; course-builder/admin agents use
file and image tools without learner gate or memory tools. Product actions such
as `append_section` and `update_section` compile to writes in
`canvas/student/*.md`, `canvas/components/*.yaml`, and `canvas/student-assets/`.

The agent may navigate this image only through typed tools. It should not freely
read host paths, mutate official source files, duplicate large course assets
into learner folders, or use browser-supplied ids as authority.

## Course Material And Workspace Seeding

Professor material is private. Do not commit raw lecture sources, PDFs, course
assets, learner workspaces, or `.lecturepilot/` contents.
The 300-line file guideline applies to code and authored repository docs, not
to gitignored uploaded course sources or professor material.

Gitignored private roots include `local-course-materials/`, `course-materials/`,
`lecture-materials/`, `prof-course-files/`, `content/private/`,
`content/courses/`, `data/courses/`, `workspaces/`, and `.lecturepilot/`.

For local demos, keep the private source slice in
`local-course-materials/<course-slug>/`. For Overleaf-backed courses, sync the
full professor checkout there and exclude only source-control metadata:

```bash
rsync -a --exclude '.git/' "$OVERLEAF_CHECKOUT/" local-course-materials/<course-slug>/
```

Override it only when needed:

```bash
export LECTUREPILOT_COURSE_MATERIAL_ROOT=/absolute/path/to/private/course
```

The professor/admin staging endpoint accepts the file types listed in
`WorkspacePolicy.allowed_course_material_uploads` and rejects unsafe paths,
unsupported suffixes, oversized payloads, and non-professor roles.

Learner writes use `users/<user-key>/courses/...`. The old
`workspaces/students/` root and compiled `canvas.json` files are retired; nothing
reads them. One-time storage changes are `storage_migration_<topic>.py` modules
(`migrate(storage_root, *, apply)`, idempotent, dry run by default) registered in
`storage_migrations.py`; the API applies pending ones in its lifespan before serving
and records them in `.storage-migrations.json`. Inspect with
`python -m lecturepilot.storage_migrations [--apply]`. Append new migrations; never
reintroduce read-time rewrites of stored data.

The Markdown files under `canvas/` are the editable source of truth.

Canvas Markdown supports these source-backed learning blocks:

- paragraphs with light Markdown and LaTeX
- `![caption](asset:relative/course/path.png)` for course assets
- `![caption](/workspace-assets/.../student-assets/file.jpg)` for learner assets
- YouTube links such as `[title](https://youtu.be/...)`
- Markdown tables
- math fences with ```math
- `:::prediction Before you begin ... :::` for one optional ungraded first guess
- `:::checkpoint Title ... :::`
- `:::quiz Title ... - option :::`

Use explicit block comments such as
`<!-- block id="risk-check" type="checkpoint" -->` when generated content needs
stable focus/highlight ids. Quiz blocks use `text` as the question and `items`
as possible answers. Checkpoint blocks use `text` as the evidence the student
must produce before a gate can pass.

## Repository Map

```txt
apps/api/                 FastAPI backend, policies, harness contracts
apps/document-converter/  Optional (compose profile "authoring") Office/PDF/OCR conversion
apps/latex-compiler/      Isolated, bounded TeX-to-PDF preview service
apps/web/                 React/Vite app and UI tests
docs/                     Architecture, workspaces, self-hosting, security notes
deploy/                   Docker Compose starter
integrations/tuebingen/   TUE API wrapper integration notes
```

Backend packages under `apps/api/src/lecturepilot/` (entry points such as `app.py`,
`database.py`, `production_preflight.py`, `bootstrap_admin.py` and
`storage_migrations.py` stay at the package root):

```txt
analytics/           learner and professor analytics, outcome events
authoring/           canvas draft generation, quality, repair, publication
canvas/              canvas Markdown/models/store, annotations, predictions, languages
core/                shared API models, storage layout, durable files, audit, observability
courses/             course access, schedules, updates, sharing, university courses
exams/               exam readiness, practice exams, PPI exam sources
identity/            auth, sessions, CSRF, tenancy, accounts, Tuebingen adapter
learner/             gates, coaching, assessments, review queue, profile and memory
learning_design/     learning intent, goals, practice and teaching design, learning maps
llm/                 model clients, provider routing, image generation, usage quotas
migrations_storage/  storage migration steps run by storage_migrations.py
sources/             source upload, routing, normalization, PDF/LaTeX/OCR processing
tutor/               tutor agent turn, typed tools, prompts and response schema
```

Frontend folders under `apps/web/src/` (`main.tsx`, `App.tsx`, `AppRoutes.tsx`, App
integration tests and global entry stylesheets stay at the root; tests and CSS sit
beside their owners):

```txt
admin/ auth/ canvas/ dashboard/ exam/ i18n/ info/ lesson/ performance/
professor/ profile/ shared/ shell/ speech/ test/
```

## Agent Harness Rules

- Authoring contract: every lecture ends as a professor-reviewable draft or one concrete
  question. Deterministic invariants (schema, source anchors, approved goal IDs/order,
  backend-inserted checkpoints, math/asset validity) may block; model reviewers and critics
  only annotate and trigger at most one targeted repair. Remaining findings are shown to the
  professor as warnings and never fail a job. Do not add new LLM vetoes after incidents;
  improve prompts against the golden-course benchmarks instead.
- Workflows, not agents: goal proposal, teaching implementation and canvas authoring are fixed
  sequences of structured calls. Repairs are stateless (current artifact + findings), never a
  replayed transcript. Saved artifacts are the resume points.
- Goals (`course_learning_intent_proposal.py`): one proposal, one advisory source-support review
  (`learning_goal_support.py`), at most one targeted repair that is not re-reviewed. The lecture
  objective is derived from the goal outcomes (also after professor edits); findings carry
  status `open` or `repaired_unchecked` and are served by `GET .../practice-design/intent/findings`.
  Approval is deterministic.
- Teaching (`teaching_design_job.py`): one structured call per missing goal, bounded in parallel,
  validated by `TeachingDesignWorkspace.write`; one lecture review; one repair per flagged goal,
  not re-reviewed (addressed findings are labelled). A canvas design conflict reuses that review
  and repairs only the named goals. AI-owned implementations keep unresolved findings as warnings.
- Canvas (`authoring_job.py`): one Markdown call per missing section with per-section
  deterministic checks; colliding generated block ids are renamed lecture-wide; one critic call
  over the whole lecture (split only above a bounded size) that classifies checkpoint objections
  (dismiss / repair_section / design_conflict) with deterministically verified evidence IDs
  (`course_canvas_quality_checkpoints.py`); one repair per flagged section, never re-reviewed
  (remaining notes become draft warnings). A verified `design_conflict` triggers exactly one
  teaching repair; the follow-up job reuses sections whose input fingerprint
  (`section-inputs.json`, `authoring_reuse.py`) is unchanged. Each section prompt sees only its
  own checkpoint contracts. Professor repair requests regenerate only sections they name. Prose writes formulas
  as `$...$`; LaTeX inside inline code (`canvas_inline_code_math.py`) and source page citations
  in generated tasks (`assessment_prompts.py`) are deterministic, repairable section defects.
- Private `builder/authoring-jobs/<lecture>/<generation>/` contains drafts and metrics.
  Status exposes metadata from `builder/authoring-metrics/`, never source-bearing content.
- Authoring calls have no tools, shell, network or learner-memory access. Approved checkpoints
  are backend-inserted. Never rewrite genuine approvals. Revision-only checks use
  `course_builder_source_revision`, not document import. Schema validity is not semantic
  truth. Do not confuse "choose one" with a uniquely correct answer.

- Tutor prompts are assembled by `tutor_prompt.py` in cache order: content shared by every
  learner of a lecture (rules, tools, a learner-independent response schema, published outline)
  first; learner sections, gate rubric, memory, coaching state and history only after the cache
  boundary. Navigation ids are validated server-side after the response (fail closed), not via
  per-learner schema enums. A turn makes at most 4 model requests; output caps follow the turn's
  intent (`tutor_turn_budget.py`) and quota reservations follow the cap.
- Background generation jobs (canvas drafts, practice exams) share the bounded slots in
  `generation_slots.py`; extra jobs wait. Lease and heartbeat file I/O runs off the event loop.
- Keep lecture unlocks backend-enforced: `lecture.date <= today` is not a
  prompt instruction.
- Attendance changes agent behavior; it must not fork the workspace schema.
  It persists in the learner's `attendance.json` (dashboard `PUT .../attendance`
  or a tutor turn) and is returned by `/courses/{id}/lectures`.
- The tutor should lead the session, ask targeted checks, and only pass quality
  gates after meaningful evidence from the student.
- Explicit checkpoint submissions use one structured assessment call, without
  filesystem tools. Even an incomplete answer requires an assessment. The
  backend derives the next approved check and assistance from that assessment;
  the provider must not choose or return `next_check`.
  Chat requires a null assessment. Ordinary checkpoints without a reviewed
  task bank or hint ladder allow an unassisted retry after a wrong answer.
- Tutor turns carry the learner's UI `locale`; backend-written learner text such as
  assessment results uses it, while stored gate reasons stay stable English audit text.
- Readiness feedback is written in the request's `feedback_locale` (else the
  course language), stated to the grader rather than inferred from the answer.
- Exam-readiness submissions use the typed API action and scaffold policy over
  the selected task, source excerpt, rubric, and course progress summary; they
  are not a general agent filesystem tool.
- Readiness feedback comes after an attempt, stays source-backed, never keyword
  auto-passes, and uses less guidance for stronger learners.
- Readiness analytics use task ids, attempt index, correctness, status, and
  source ids; do not treat raw time as primary or expose learner text in
  professor aggregates.
- Practice exams remain separate from Exam Readiness: they are immutable,
  source-grounded 20–30 question simulations. Explicit submissions persist private,
  immutable answers; drafts stay in the browser tab. There is no server-side
  grading. A separate post-attempt solution sheet may score
  multiple choice locally and provide full-credit reference answers for
  self-review.
  `practice_exam_generation_service.py` owns background generation and
  `practice_exam_lease.py` renews its durable lease; HTTP 202 clients poll the same key.
  The tutor receives bounded, lecture-scoped history from saved readiness results
  and practice submissions. Practice answers remain ungraded, assistance unknown;
  history never passes gates. Students can review/delete their own submissions.
  PPI protocols may inform question patterns only; every question must remain
  anchored to unlocked published course evidence and must not copy protocol
  wording.
- Before canvas generation, the source-routing agent must semantically assign
  every indexed course file exactly once as lecture-specific, course-wide, or
  not used. Professors review and may edit this complete proposal; generation
  remains blocked until the current source revision is confirmed. A first proposal is
  confirmed automatically (`course_source_routing_auto_accept.py`, no model call) only when it
  deletes no upload, needs no OCR, gives every lecture its own material and routes each
  scheduled main file to its lecture; it stays editable. Confirmation prunes unused uploads and
  normalized copies while preserving selected-source dependencies and existing
  workspace references; index and routing revisions update transactionally.
- After source confirmation, automatically propose missing source-backed learning goals without tasks.
  "Approve all open goals" is the primary action; per-lecture approval stays available, and each
  current approval advances that lecture to draft generation. Refresh
  (`intent/proposal?refresh=true`) replaces unapproved goals only.
  Professors approve outcomes, constraints and explicitly fixed tasks. Teaching
  implementations are AI-owned until publication and may be repaired without changing
  approved intent; a design whose tasks are all professor-fixed is never AI-repaired (a
  conflict asks for plan review). Schema 1 is retired: its full approvals were migrated to
  fully fixed goal approvals (`storage_migration_practice_design_schema.py`).
  See `docs/learning-intent-ownership.md`.
- Same-source implementation repair preserves every approved goal, ordered ID,
  constraint and fixed task. It cannot evade an assessment by dropping its goal.
  Goal/source edits need new intent approval; implementation repair preserves it.
- Practice-design providers select request-local evidence IDs from
  `practice_evidence_catalogue.py`; the backend hydrates exact routed quotations
  and derives source paths. Semantic support still requires review.
- Generation receives exact approved intent and a reviewed implementation and
  writes source, intent and implementation revisions to the draft binding. Draft review and
  publication fail closed when that binding, design approval, or source
  revision is no longer current; regenerate rather than infer a replacement.
- A generated canvas may become ready only after deterministic learning-design
  defects have passed validation or targeted repair. "Approve & publish"
  (`course_canvas_approval_publication.py`) binds the exact draft digest, source revision and
  practice-design revision and publishes in one course lock, rolling the approval back if
  publication fails; map or report edits clear it. It does not replace the earlier goal
  approval or acknowledge generator diagnostics as a separate publication task.
- Place each approved practice checkpoint in its outcome-anchor section, not
  the first section matching an auxiliary hint. The backend inserts approved checkpoints and
  validates exact task ids/text document-wide; generic formatting must preserve them.
- Section output has native exact-one cardinality; the backend inserts approved
  checkpoints. Repair schemas bind exact target IDs/counts, and repair prompts
  receive only their section's targets. Cross-section approved source excerpts
  may support teaching, but hidden assessment wording must not be forwarded.
- Source grounding permits accurate explanations of source-named concepts and derivations
  from supplied definitions or formulas. Authoring and review must apply the same boundary;
  missing verbatim wording alone is not an unsupported claim.
- Shared authoring guidance lives in `course_teaching_instructions.py`. Forward
  approved learner context into canvas generation without exposing hidden exit
  tasks. Canonical diagnostics may precede worked examples; ordinary formative
  checks follow them. Keep generation validation and draft reports consistent.
- This slice records future independent-exit and scaffold intent only. It does
  not assert learner efficacy or add learner-runtime SRL or AI-policy enforcement.
- Canvas commands may focus sections, highlight specific blocks or phrases, and
  append/update learner-specific Markdown sections.
- Private passage comments are files under `/lecture/annotations/<name>.json`.
  Use ordinary `write`, `read`, and `edit`; the adapter validates `block_id`,
  `quote`, and Markdown `comment`, and owns publication/identity metadata. Markers
  reopen comments; learners can delete them. Independent attempts hide comments.
- Learner Markdown uses `placement_mode` and `placement_section_id` frontmatter
  for contextual insertion. New unplaced sections follow the current focus;
  rewrites preserve saved placement. Official sections remain immutable.
- Infographic requests may call the backend image-generation tool. Provider
  raster images are stored under the learner workspace. Do not generate local
  SVG fallback infographics.
- Tool calls shown in the chat should correspond to real harness actions.
- Generated learner content belongs in `canvas/student/*.md`, not in official
  source sections.
- Durable personalization belongs in user memory files, not in prompt-only
  state. Use structured JSON for enforceable cross-course preferences,
  Markdown for rich tutor memory, course memory for course-specific teaching
  observations, and `memory-trace.jsonl` for provenance.

## Learning Evidence And Teaching Languages

- Prediction cards save a private first guess or skip, bound to the published
  block digest and revision. They never pass gates or enter professor analytics.
  New authoring may include at most one per lecture; professor preview is read-only.
  See `docs/canvas-predictions.md`.

- Reviewed supplemental task banks belong to private practice designs and learning
  maps. Never forward their hidden questions into teaching generation.
- Approved hints may bind target-local rubric `evidence_ids`; assessment transitions
  select unexposed relevant support and persist the triggering evidence and selected
  level. Preserve legacy approval digests and independent-attempt rules.
- Help requests bind gate revision, task ID and issuance time and persist support
  before revealing materials. Supported work needs a fresh reviewed task for
  independent evidence; bank exhaustion stays explicit.
- Focused attempts hide teaching, notes, sources and chat. Wait for learner state
  on reload; do not flash materials before resolving a pending independent task.
- German/English explanation variants require exact-digest professor publication.
  Preserve canonical assessments, formulas, code and source identities. Bind to
  current canonical publication; never substitute a stale translation.
- AI implementation repair reports live in private practice-design history and
  show deterministic before/after values and recorded reasons. See
  `docs/learning-evidence-flow.md` for ownership and storage paths.

## UI And Canvas Rules

- The student dashboard shows per-lecture and course progress, newest unlocked lectures first,
  "New since your last visit" markers (`course_last_visit.py`, learner `last-visit.json`) and one
  "Next up" card (best next action, due reviews, ICS export). The course workspace has two tabs:
  Lectures and Exam prep, whose modes are the quick graded readiness check and the full mock
  practice exam (with PPI import).
- Course search (`lecture_search.py`, `learner_study_routes.py`) covers only released, published
  teaching blocks the learner may access; never checkpoints, quizzes, predictions, components or
  hidden assessment content, and never logs query text. Learners can export their own tutor
  notes for a lecture as Markdown (`learner_notes_export.py`).
- Frontend polling goes through `polling.ts` (backoff, pauses in hidden tabs, cancels on unmount,
  overall deadline, honours Retry-After). Professors with courses land on course management;
  the first-visit professor tour is lazy-loaded for course managers only.

- Public information pages use `InfoArticle.tsx` with bilingual content modules.
  Keep privacy disclosures aligned with deployment, memory and deletion behavior;
  see `docs/product-information-pages.md`. The How it works guide also opens the
  public chaptered onboarding video.

- Professor onboarding video and chapter descriptions live in `OnboardingVideo.tsx`
  and `onboardingChapters.ts`. Versioned public media is tracked under `docs/onboarding-media/`,
  mounted read-only into the web service; see `docs/onboarding-video.md`.

- Legacy publications remain visible to their owner in course management as disabled Legacy courses
  with a recreate notice and deletion as their only action. `course_legacy_publication.py` identifies the obsolete metadata;
  `course_access_summary.py` keeps invalid content unavailable while management stays usable.
  The Private label reflects instructor-only defaults and lecture audiences.

- Course creation has five visible stages: Course, Materials, Media, Learning plan,
  and Review & publish. Materials owns source confirmation; the separate Media
  stage offers video selection or continuing without videos before learning-plan review. The
  final stage owns draft generation and per-lecture "Approve & publish" plus "Approve &
  publish all ready". Builder resume/retry decisions live in the pure reducer
  `builderFlowMachine.ts`; the builder hooks are split by stage (`useBuilder*.ts`).
  Course management labels setup state (incomplete, partly published, published) and
  offers "Continue setup"; `writeResumeFlow` seeds the builder and backend restore picks the
  step. "Create course" there always starts empty; the builder names the course in progress.
  Each lecture drafts as soon as its goals are approved (a changed, re-approved plan drafts
  again); ready lectures are approved and published independently.
- Course support requests: unmatched Alma/ILIAS courses in the student dashboard offer "Request
  LecturePilot" (`CourseSupportRequest.tsx`, `courseSupportApi.ts`) with an aggregate count; platform
  admins (`tenant_admin`) get the "Course demand" page (`admin/CourseDemandPage.tsx`,
  `/platform/course-demand`); the builder course step shows `CourseDemandHint.tsx`. Backend:
  `courses/course_support_{requests,demand,routes,models}.py` over Postgres
  `course_support_requests` (cascade from `users`). Requests accept only the `source`,
  `external_course_id` and `term` of the session user's own stored observation (404 otherwise);
  title matching reuses `course_title_key`. Every surface returns tenant-scoped counts only, never
  identities; the professor builder match reports request counts only from 3 upward; audit rows
  carry only request ID and source.
- Sharing: course management "Share" shows the course link `/courses/<id>` with a local QR code
  and a slide image; access follows Alma/ILIAS enrollment. "Allow joining with this link" is an
  explicit opt-in (`course_invites.py`) that creates a revocable `/join/<id>/<secret>` link;
  joining writes an `invite` enrollment that university sync never deactivates. Unauthenticated
  link visitors see only a generic intro; join previews show title, term and lecture count.

- The canvas is the main learning surface and should remain the single ground
  truth for generated explanations, quizzes, examples, figures, and summaries.
  Render the revision-matched pending check at its checkpoint after reload; do
  not overwrite published tasks or carry a previous answer into a changed task.
- Side panels are navigation and inspection aids; do not move core learning
  content into a side panel unless the user explicitly asks.
- Learner sidebar modes are Tutor, Document outline, and files. The outline owns
  section navigation and practice evidence; do not reintroduce separate path or
  metadata-only notes panels. Practice checks do not unlock subsequent sections.
- Source references must stay in-app. Do not use direct links that navigate the
  browser away from LecturePilot for course assets or source traces.
- Prefer compact, readable controls. Avoid gradients, decorative blobs, nested
  cards, or marketing-page composition in the learning workspace.
- Support light and dark mode for new UI surfaces.

## Security And Data Rules

- Treat course uploads and LaTeX/PDF/image assets as untrusted input.
- Never compile uploaded TeX inside the API process. Use the no-secret,
  internal-only compiler service; matching uploaded PDFs remain authoritative.
- Office/PDF/OCR conversion runs only in the optional `document-converter` service (compose
  profile `authoring`, started while courses are built). When it is unreachable, conversion and
  drafting fail with an actionable 503; never fall back to degraded parsing.
- Never commit private professor material, real credentials, provider keys, or
  learner workspace data.
- PPI credentials are request-only. Retained PPI archives and normalized text
  remain private below the authenticated learner course root until the learner
  deletes the source, resets that course workspace, or deletes the account.
- Reject hidden paths, absolute paths, `..` traversal, unsupported extensions,
  and oversized files in backend file APIs.
- Derive tenant/course/user authority from backend session/profile context, not
  browser-controlled ids.
- A state change carrying an ended (revoked or unknown) session gets 401 from the CSRF
  middleware, not 403; `apiRequest` reports 401s through `sessionSignals.ts` so the session
  hook re-checks and shows the sign-in-again notice.
- Keep raw user identifiers out of filesystem paths; use hashed prefixes.
- Keep outcome events categorical and revision-bound. Gate outcomes may copy
  assistance and planned/observed delay only from the exact stored coaching
  turn; do not add learner text, conditions, randomization, or browser timing.
- Production already has durable quotas and audit events. Preserve the path
  toward approved retention/deletion plus object storage and signed URLs if
  protected files move off authenticated API routes.

## Engineering Standards

- Prefer test-driven changes: write or update the failing regression test first
  when behavior is specified, then implement the smallest fix that passes it.
- Never take the course lock (`locked_course_state`, a blocking flock) or parse
  course sources inside `async def`; use `run_in_threadpool`. Never parse sources
  (conversion, LaTeX, PDF, OCR) while holding the course lock: snapshot, parse,
  then re-check the revision. `test_event_loop_blocking.py` enforces both.
- Keep files under 300 lines. Split by ownership before adding more behavior to
  large files. This rule applies to code and authored repo docs, not ignored
  course material.
- Keep diffs surgical. Do not refactor unrelated code, reformat files, or
  preserve rejected experiments unless the current task needs it.
- Remove dead code, stale compatibility paths, fake fallbacks, mock behavior,
  and duplicate implementations once the real path exists.
- Use structured contracts at boundaries: Pydantic models and schemas in the
  API, TypeScript types in the UI, and explicit Markdown/component formats for
  canvas files.
- Prefer provider/framework-native features over prompt-only conventions. For
  example, use provider `response_format`/schema support when the backend relies
  on structured model output.
- Check current official docs or local source before changing provider,
  framework, auth, storage, or model API behavior.
- Keep agent tools real. Chat-visible tool calls must map to backend actions or
  constrained filesystem writes, not to simulated UI tags.
- Do not add configurability, mock data, or fallback flows unless the user asked
  for them. Fail clearly when required credentials or services are missing.

## Development Workflow

- Start by reading the existing module and tests that own the behavior.
- For a bug: reproduce narrowly, add a regression test, fix, then rerun the
  narrow test and the relevant broader suite.
- For UI behavior: verify in the browser at `http://127.0.0.1:5173`, exercise
  the changed workflow, and check for console errors.
- For model behavior: use deterministic unit tests for parser/tool contracts and
  use benchmarks for provider quality. Benchmarks inform decisions but should
  not become flaky CI gates.
- For security/privacy: verify auth headers, role checks, path validation, and
  logout or unauthenticated access in the real API/browser path.
- Before finishing, summarize what was verified and what was not.

## Verification Commands

Run the narrowest meaningful check first, then broaden:

```bash
npm run verify:fast
npm run verify:api
npm run verify:web
npm run verify:full
```

Provider benchmark:

```bash
python scripts/benchmark_gate_models.py --model gemini/gemini-3.1-flash-lite
```

Practice-exam scope and solution-quality comparisons use
`scripts/benchmark_practice_exams.py`; see
[`docs/practice-exam-benchmark.md`](docs/practice-exam-benchmark.md).
Keep human-labelled fixtures and source-bearing reports private below
`.lecturepilot/benchmarks/`. Generated-exam acceptance is a diagnostic, not
independent correctness or learner-efficacy evidence.

File-size guard:

```bash
find apps/api/src apps/api/tests apps/web/src -type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.css' \) -print0 | xargs -0 wc -l | awk '$2 != "total" && $1 > 300 { print }'
```

CI lives in `.github/workflows/ci.yml` and invokes `verify:api` and `verify:web`
after its database migration check. Keep local verification aligned with those
package scripts unless deliberately changing CI.

## Contribution Notes

- Use conventional commit prefixes such as `feat:`, `fix:`, `docs:`, `test:`,
  and `chore:`.
- Group commits by logical change when unrelated edits exist in the worktree.
- Include tests or state exactly why a change is docs-only or not testable.
- Update `README.md`, `docs/`, and this file when changing setup, workspace
  layout, security policy, module ownership, or development workflow.
- If instructions conflict, the nearest `AGENTS.md` wins. Explicit user
  instructions in chat override repository guidance.
