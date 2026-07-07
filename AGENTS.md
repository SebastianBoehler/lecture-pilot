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
uvicorn lecturepilot.app:app --app-dir apps/api/src --reload
npm run dev --workspace apps/web
```

Open `http://127.0.0.1:5173`. Use **Preview local demo** for local UI and
agent-flow checks without sending real credentials.

## Agent Storage Image

The agent should be seeded with a clear filesystem image. Treat this as the
logical structure even when production storage is backed by Postgres and object
storage instead of local folders.

```txt
.lecturepilot/
  users/<user-key>/
    profile.json
    memories/{global.md,preferences.json,memory-trace.jsonl}
    courses/<course-id>/
      progress.json
      memories/{course.md,memory-trace.jsonl}
      lectures/<lecture-id>/
        {attendance.json,gates.json,tutor-state.json}
        canvas/{student/*.md,components/*.yaml,student-assets/*}
  courses/<tenant-id>/<course-id>/
    course.json
    source/{uploads/,normalized/,assets/,source-index.json}
    canvas/lectures/<lecture-id>/{index.md,sections/*.md,assets/}
    builder/{drafts/,review-state.json}
  cache/{pdf-previews/,thumbnails/,extracted-text/}
```

Official source material belongs to `courses/<tenant>/<course>/source`.
Professor-approved learning documents belong to
`courses/<tenant>/<course>/canvas`. Cross-course teaching preferences belong to
`users/<user-key>/memories`. Lecture-specific attendance, gates, progress,
generated notes, and generated images belong under the user's course/lecture
workspace.

Global memory records cross-course teaching preferences. Course memory records
course-specific tutoring observations. `memory-trace.jsonl` stores append-only
provenance for memory writes, including the course, lecture, tool, and note.

The agent uses a small set of low-level typed tools over this image. Default
tutor gets `pwd`, `ls`, `read`, `write`, `edit`, `focus`, `highlight`,
`generate_image`, `record_gate`, `record_readiness_attempt`, and `remember`.
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

The current local implementation still writes learner overlays into the older
`.lecturepilot/workspaces/students/<sha256-user-prefix>/courses/<course-id>/`
path. The target structure is the `users/<user-key>/courses/...` image above.
Keep new work moving toward that split instead of adding more behavior to the
legacy `workspaces/students` path.

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
apps/web/                 React/Vite app and UI tests
docs/                     Architecture, workspaces, self-hosting, security notes
deploy/                   Docker Compose starter
integrations/tuebingen/   TUE API wrapper integration notes
packages/                 Future package boundaries/placeholders
services/agent/           Future external agent runtime notes
```

Important API modules: `app.py`, `canvas_workspace.py`,
`canvas_markdown.py`, `source_bundle.py`, `harness.py`, `model_client.py`,
`image_generation*.py`, `policies.py`, `providers.py`, `tenancy.py`,
`tuebingen_adapter.py`, and `workspace.py`.

Important web modules: `App.tsx`, `Dashboard.tsx`, `LessonWorkspace.tsx`,
`LessonCanvas.tsx`, `SectionSources.tsx`, `SourceMarker.tsx`,
`WorkspaceFilesPanel.tsx`, `TutorDrawer.tsx`, `api.ts`, and `types.ts`.

## Agent Harness Rules

- Keep lecture unlocks backend-enforced: `lecture.date <= today` is not a
  prompt instruction.
- Attendance changes agent behavior; it must not fork the workspace schema.
- The tutor should lead the session, ask targeted checks, and only pass quality
  gates after meaningful evidence from the student.
- Exam-readiness turns use `record_readiness_attempt` and typed scaffold policy
  over the selected task, source excerpt, rubric, and course progress summary.
- Readiness feedback comes after an attempt, stays source-backed, never keyword
  auto-passes, and uses less guidance for stronger learners.
- Readiness analytics use task ids, attempt index, correctness, status, and
  source ids; do not treat raw time as primary or expose learner text in
  professor aggregates.
- Canvas commands may focus sections, highlight specific blocks or phrases, and
  append/update learner-specific Markdown sections.
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

## UI And Canvas Rules

- The canvas is the main learning surface and should remain the single ground
  truth for generated explanations, quizzes, examples, figures, and summaries.
- Side panels are navigation and inspection aids; do not move core learning
  content into a side panel unless the user explicitly asks.
- Source references must stay in-app. Do not use direct links that navigate the
  browser away from LecturePilot for course assets or source traces.
- Prefer compact, readable controls. Avoid gradients, decorative blobs, nested
  cards, or marketing-page composition in the learning workspace.
- Support light and dark mode for new UI surfaces.

## Security And Data Rules

- Treat course uploads and LaTeX/PDF/image assets as untrusted input.
- Never commit private professor material, real credentials, provider keys, or
  learner workspace data.
- Reject hidden paths, absolute paths, `..` traversal, unsupported extensions,
  and oversized files in backend file APIs.
- Derive tenant/course/user authority from backend session/profile context, not
  browser-controlled ids.
- Keep raw user identifiers out of filesystem paths; use hashed prefixes.
- Production work should preserve the path toward signed URLs, quotas, audit
  logs, retention, deletion, and object storage.

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
pytest apps/api/tests -q
npm run test --workspace apps/web
npm run build --workspace apps/web
git diff --check
```

Provider benchmark:

```bash
python scripts/benchmark_gate_models.py --model gemini/gemini-3.1-flash-lite
```

File-size guard:

```bash
find apps/api/src apps/api/tests apps/web/src -type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.css' \) -print0 | xargs -0 wc -l | awk '$2 != "total" && $1 > 300 { print }'
```

CI lives in `.github/workflows/ci.yml` and runs API tests, web tests, and the
web build. Keep local verification aligned with CI unless deliberately changing
CI.

## Contribution Notes

- Use conventional commit prefixes such as `feat:`, `fix:`, `docs:`, `test:`,
  and `chore:`.
- Group commits by logical change when unrelated edits exist in the worktree.
- Include tests or state exactly why a change is docs-only or not testable.
- Update `README.md`, `docs/`, and this file when changing setup, workspace
  layout, security policy, module ownership, or development workflow.
- If instructions conflict, the nearest `AGENTS.md` wins. Explicit user
  instructions in chat override repository guidance.
