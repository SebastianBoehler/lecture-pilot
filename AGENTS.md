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

Install frontend dependencies:

```bash
npm install
```

Create the API environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e "apps/api[test,agent]"
```

Add Uni Tuebingen wrapper support only when working on live university login:

```bash
pip install -e "apps/api[tuebingen]"
```

If developing against a local wrapper checkout:

```bash
pip install -e ../tue-api-wrapper/package
```

## Dev Servers

Run API:

```bash
source .venv/bin/activate
uvicorn lecturepilot.app:app --app-dir apps/api/src --reload
```

Run web app:

```bash
npm run dev --workspace apps/web
```

Open `http://127.0.0.1:5173`. Use **Preview local demo** for local UI and
agent-flow checks without sending real credentials.

## Course Material And Workspace Seeding

Professor material is private. Do not commit raw lecture sources, PDFs, course
assets, learner workspaces, or `.lecturepilot/` contents.

Gitignored private roots include:

```txt
local-course-materials/
course-materials/
lecture-materials/
prof-course-files/
content/private/
content/courses/
data/courses/
workspaces/
.lecturepilot/
```

For the Martius demo, point the API at the private Overleaf checkout containing
`Lecture03-eng.tex`:

```bash
export LECTUREPILOT_COURSE_MATERIAL_ROOT=/absolute/path/to/private/course
```

On first lecture open, the API imports LaTeX into a learner workspace:

```txt
.lecturepilot/workspaces/
  students/<sha256-user-prefix>/
    courses/<course-id>/
      lectures/<lecture-id>/
        canvas/
          index.md
          sections/*.md
          student/*.md
        canvas.json
```

The Markdown files under `canvas/` are the editable source of truth. Treat
`canvas.json` as a compiled API cache/artifact, not as the primary authoring
format.

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

Important API modules:

```txt
app.py                    FastAPI routes
canvas_workspace.py       workspace lifecycle and canvas loading
canvas_markdown.py        Markdown canvas compiler
latex_canvas_importer.py  LaTeX-to-canvas import grouping
guided_tutor.py           local deterministic tutor behavior
harness.py                agent turn contract
model_client.py           provider-backed model call boundary
policies.py               lecture unlock and workspace file policies
providers.py              provider readiness/capability checks
tenancy.py                tenant/profile/role models and gates
tuebingen_adapter.py      TUE API wrapper boundary
workspace.py              path, type, and size validation
```

Important web modules:

```txt
App.tsx                   top-level app state and API wiring
Dashboard.tsx             course and lecture selection
LessonWorkspace.tsx       lesson shell, right rail, panel routing
LessonCanvas.tsx          rendered learning document
SectionSources.tsx        numbered source references per section
SourceMarker.tsx          inline source citation buttons
WorkspaceFilesPanel.tsx   in-app file/source/asset preview drawer
TutorDrawer.tsx           text-only guided tutor chat
api.ts                    frontend API client
types.ts                  shared frontend data contracts
```

## Agent Harness Rules

- Keep lecture unlocks backend-enforced: `lecture.date <= today` is not a
  prompt instruction.
- Attendance changes agent behavior; it must not fork the workspace schema.
- The tutor should lead the session, ask targeted checks, and only pass quality
  gates after meaningful evidence from the student.
- Canvas commands may focus sections, highlight specific blocks or phrases, and
  append/update learner-specific Markdown sections.
- Tool calls shown in the chat should correspond to real harness actions.
- Generated learner content belongs in `canvas/student/*.md`, not in official
  source sections.

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

## Code Style

- Match the existing architecture and naming.
- Keep files under 300 lines. If a file approaches that, split by ownership
  before adding more behavior.
- Keep changes surgical. Do not refactor unrelated code while fixing a specific
  behavior.
- Use TypeScript types and Pydantic models for structured data.
- Use parsers/typed helpers for course and canvas data. Avoid ad hoc string
  surgery when a structured module already exists.
- Add focused tests for behavior changes.

## Testing Instructions

Run the narrowest meaningful check first, then the broader suite before
finishing.

API tests:

```bash
pytest apps/api/tests -q
```

Web tests:

```bash
npm run test --workspace apps/web
```

Web build:

```bash
npm run build --workspace apps/web
```

Whitespace check:

```bash
git diff --check
```

File-size guard:

```bash
find apps/api/src apps/api/tests apps/web/src -type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.css' \) -print0 | xargs -0 wc -l | awk '$2 != "total" && $1 > 300 { print }'
```

For rendered UI changes, verify the running app in a browser at
`http://127.0.0.1:5173`, exercise the changed interaction, and check the
console for relevant warnings/errors.

## CI

CI lives in `.github/workflows/ci.yml` and runs:

- `pytest apps/api/tests`
- `npm run test --workspace apps/web`
- `npm run build --workspace apps/web`

Keep local verification aligned with CI unless deliberately changing CI.

## Contribution Notes

- Use conventional commit prefixes such as `feat:`, `fix:`, `docs:`,
  `test:`, and `chore:`.
- Group commits by logical change when multiple unrelated edits exist.
- Include tests or explain exactly why a change is not testable yet.
- Update `README.md`, `docs/`, and this file when changing setup, workspace
  layout, security policy, or module ownership.
- If instructions conflict, the nearest `AGENTS.md` wins. Explicit user
  instructions in chat override repository guidance.
