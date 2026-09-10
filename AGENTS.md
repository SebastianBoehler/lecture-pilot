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

## Agent Storage Image

The agent should be seeded with this logical filesystem image. Production keeps
database authority in Postgres and files on the persisted `/app/storage` volume.

```txt
.lecturepilot/
  users/<user-key>/
    profile.json
    memories/{global.md,preferences.json,memory-trace.jsonl}
    courses/<course-id>/
      progress.json
      exam-sources/ppi/<ppi-lecture-id>/{manifest.json,source.zip,normalized/}
      practice-exam-generations/<request-key-hash>.json
      practice-exams/<exam-id>/{exam.json,exam.pdf,solutions.pdf,attempts/<uuid>.json}
      memories/{course.md,memory-trace.jsonl}
      lectures/<lecture-id>/
        {attendance.json,gates.json,tutor-state.json}
        annotations/<name>.json
        canvas/{student/*.md,components/*.yaml,student-assets/*}
  courses/<tenant-id>/<course-id>/
    course.json
    source/{uploads/,normalized/,source-index.json}
    canvas/lectures/<lecture-id>/{index.md,sections/*.md,assets/}
    canvas-drafts/lectures/<lecture-id>/latest/{...,practice-design-binding.json}
    builder/{generations/,practice-designs/<lecture-id>.json,repairs/,source-manifests/,source-routing.json,updates/}
    builder/implementation-jobs/<lecture-id>/<identity>/{draft.json,session.json}
```

Official source material belongs to `courses/<tenant>/<course>/source`.
Professor-approved learning documents belong to
`courses/<tenant>/<course>/canvas`. Cross-course teaching preferences belong to
`users/<user-key>/memories`. Lecture-specific attendance, gates, progress,
generated notes, and generated images belong under the user's course/lecture
workspace.

The agent uses a small set of low-level typed tools over this image. Default
tutor gets `pwd`, `ls`, `read`, `write`, `edit`, `focus`, `highlight`,
`generate_image`, `record_gate`, and `remember`.
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

New learner writes use `users/<user-key>/courses/...`. The reader still accepts
the older `.lecturepilot/workspaces/students/...` compiled canvas and asset
paths for migration compatibility; do not add new writes to that legacy root.

The Markdown files under `canvas/` are the editable source of truth. Treat
`canvas.json` as a compiled API cache/artifact, not as the primary authoring
format.

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
apps/latex-compiler/      Isolated, bounded TeX-to-PDF preview service
apps/web/                 React/Vite app and UI tests
docs/                     Architecture, workspaces, self-hosting, security notes
deploy/                   Docker Compose starter
integrations/tuebingen/   TUE API wrapper integration notes
packages/                 Reserved package boundaries; no runtime code yet
services/agent/           Reserved external-runtime boundary; runtime is in API
```

## Agent Harness Rules

- Canvas authoring uses `CourseCanvasAuthor` and the Pydantic AI loop in
  `authoring_job.py`; do not route production through the retained benchmark-only
  legacy planner. The framework owns execution, not authority or learner memory.
- Private `builder/authoring-jobs/<lecture>/<generation>/` contains native history,
  read-only evidence and editable draft files. Status exposes metadata from
  `builder/authoring-metrics/`, never source-bearing histories. Keep these private.
- Authoring tools have no shell, arbitrary network or learner-memory access.
  Approved checkpoints are backend-inserted. Verify a critic's objection against
  source, task, rubric and teaching: dismiss unsupported objections, repair missing
  teaching, and escalate only confirmed approved-design conflicts. Never rewrite
  genuine approvals. See `docs/authoring-agent-migration.md`.
- AI-owned teaching implementation uses a persistent target-scoped `read`/`write`/`validate`
  agent before canvas file authoring; semantic findings do not share the schema retry budget.
  Saved targets and history resume under the same source/intent identity.
- Learning-plan proposals and their reviewer use native-schema Pydantic AI sessions.
  Repair generated questions, rubrics, hints and variants before design approval;
  missing reviewer evidence and unknown target IDs must be corrected by the reviewer.
  Implementation output contains teaching details; the backend binds approved goal fields and
  constraints unchanged instead of asking the provider to copy them. Schema validity is
  not semantic truth. Do not confuse "choose one" with a uniquely correct answer.

- Keep lecture unlocks backend-enforced: `lecture.date <= today` is not a
  prompt instruction.
- Attendance changes agent behavior; it must not fork the workspace schema.
- The tutor should lead the session, ask targeted checks, and only pass quality
  gates after meaningful evidence from the student.
- Explicit checkpoint submissions use one structured assessment call, without
  filesystem tools. Even an incomplete answer requires an assessment. The
  backend derives the next approved check and assistance from that assessment;
  the provider must not choose or return `next_check`.
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
  The tutor receives bounded, lecture-scoped history from saved readiness results
  and practice submissions. Practice answers remain ungraded, assistance unknown;
  history never passes gates. Students can review/delete their own submissions.
  PPI protocols may inform question patterns only; every question must remain
  anchored to unlocked published course evidence and must not copy protocol
  wording.
- Before canvas generation, the source-routing agent must semantically assign
  every indexed course file exactly once as lecture-specific, course-wide, or
  not used. Professors review and may edit this complete proposal; generation
  remains blocked until they confirm the current source revision. Confirmation prunes unused uploads and
  normalized copies while preserving selected-source dependencies and existing
  workspace references; index and routing revisions update transactionally.
- After source confirmation, automatically propose missing source-backed learning goals without tasks.
  Review one lecture at a time; the final current approval advances to draft generation.
  Preserve explicit draft approval and publication.
  Professors approve outcomes, constraints and explicitly fixed tasks. Schema-2
  teaching implementations are AI-owned until publication and may be repaired
  without changing approved intent. Preserve schema-1 full approvals unless the
  professor explicitly converts them; archive earlier snapshots privately.
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
  defects have passed validation or targeted repair. Professor approval confirms
  the implementation for the exact draft, source, practice-design, report, and
  learning-map revisions; it does not replace the earlier design approval or
  acknowledge generator diagnostics as a separate publication task.
- Place each approved practice checkpoint in its outcome-anchor section, not
  the first section matching an auxiliary hint. Validate exact task ids/text
  before caching completed sections; generic formatting must preserve them.
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

- Public WebMCP tools expose the public guides without account access. Student tools
  verify the backend session and expose navigation, display settings and read-only progress only.
  Keep assessments, tutor messages, attendance and learning mutations human-owned.
  See `docs/webmcp.md`; `webMcpTools.ts` owns the allowlist and `useWebMcp.ts` registration.

- Public information pages use `InfoArticle.tsx` with bilingual content modules.
  Keep privacy disclosures aligned with deployment, memory and deletion behavior;
  see `docs/product-information-pages.md`. The How it works guide also opens the
  public chaptered onboarding video.

- Professor onboarding video and chapter descriptions live in `OnboardingVideo.tsx`
  and `onboardingChapters.ts`. Versioned public media is tracked under `docs/onboarding-media/`,
  mounted read-only into the web service; see `docs/onboarding-video.md`.

- Course creation has five visible stages: Course, Materials, Media, Learning plan,
  and Review & publish. Materials owns source confirmation; the separate Media
  stage offers video selection or continuing without videos before learning-plan review. The
  final stage owns draft generation, exact-draft approval, and publication.

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
- Never commit private professor material, real credentials, provider keys, or
  learner workspace data.
- PPI credentials are request-only. Retained PPI archives and normalized text
  remain private below the authenticated learner course root until the learner
  deletes the source, resets that course workspace, or deletes the account.
- Reject hidden paths, absolute paths, `..` traversal, unsupported extensions,
  and oversized files in backend file APIs.
- Derive tenant/course/user authority from backend session/profile context, not
  browser-controlled ids.
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
