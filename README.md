<div align="center">
  <h1>LecturePilot</h1>
  <p><strong>A lightweight, text-first course tutor for university settings.</strong></p>
  <p>
    <a href="https://github.com/SebastianBoehler/lecture-pilot/actions/workflows/ci.yml">
      <img alt="CI" src="https://github.com/SebastianBoehler/lecture-pilot/actions/workflows/ci.yml/badge.svg" />
    </a>
    <img alt="UI test suite: Vitest" src="https://img.shields.io/badge/UI%20test%20suite-Vitest-6E9FEE" />
    <img alt="API test suite: pytest" src="https://img.shields.io/badge/API%20test%20suite-pytest-3776AB" />
    <img alt="UI build: Vite" src="https://img.shields.io/badge/UI%20build-Vite-646CFF" />
    <img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-2F4858" />
  </p>
</div>

It combines a normal web app, a typed learner workspace, and a constrained agent
harness. The current university integration is University of Tübingen via
[`tue-api-wrapper`](https://github.com/SebastianBoehler/tue-api-wrapper).

## Preview

<p align="center">
  <img
    alt="LecturePilot lesson canvas showing a Bayesian Decision Theory lecture with source-backed content and workspace tools"
    src="docs/assets/lecturepilot-lesson-ui.jpg"
    width="900"
  />
</p>

## Product Flow

- Login through university credentials and synchronize the learner's own Alma
  timetable and ILIAS memberships.
- Let professors upload differently structured course folders, review/reorder a
  proposed schedule, generate and repair private lecture drafts, then publish.
- Show learners only authorized, published lectures whose access date passed.
- Ask whether the learner attended, render source-backed slides and a focused
  lesson canvas, then adapt the tutoring stance.
- Let the constrained agent highlight, explain, quiz, generate learner-owned
  study artifacts, and save progress/memory.

## Current Slice

This repository is intentionally small but runnable:

- FastAPI backend with health, course, lecture, and agent-turn endpoints.
- Strict lecture unlock policy.
- Typed workspace file policy.
- Provider capability checks with Gemini Flash-Lite as the default text model.
- Development-only credential-free demo that opens the course shell while
  tutor turns use the configured provider model. Production builds do not
  render demo access.
- React/Vite frontend with dashboard and focused lesson workspace.
- Unified TUE API login for students and professors, with the active
  Alma role verified by the backend.
- Login returns after role verification; lightweight Alma timetable and ILIAS
  membership/profile data then synchronize in parallel behind the dashboard.
- The active Alma `student` role grants learner access; any other verified Alma
  role grants professor access. Browser-selected roles are never accepted.
- Postgres-backed users, opaque sessions,
  course ownership, Alma/ILIAS enrollment evidence, audit events, and durable
  quotas.
- Capability-scoped, symlink-safe learner and course-builder workspaces.
- Uploaded lecture PDFs remain authoritative for slide previews. TeX-only
  lectures are compiled into handout previews by an isolated, no-secret
  service; failures keep the text canvas and surface a professor warning.
- Light and dark mode.
- Resumable/idempotent canvas generation with progress guidance, exact failed
  block diagnostics, and targeted **Fix with AI** repair.
- Professor course updates, lecture access scheduling, drag-and-drop lecture
  order, learner preview, usage/performance aggregates, and release notices.
- Backend and frontend tests.
- CI, Dockerfiles, and Compose starter.

Provider-backed tutor turns intentionally fail with a clear error until a real
API key is configured.

## Agent Harness

LecturePilot is an agent harness for teaching, not a generic chatbot. The agent
acts as a text-first tutor that can also build and revise the learning
interface by operating on a constrained filesystem-like workspace.

The tool model stays small and low-level with Pi-style Unix names where that
fits the filesystem image. Tools are profile-scoped:

- default tutor: `pwd`, `ls`, `read`, `write`, `edit`, `focus`,
  `highlight`, `record_gate`, `remember`, `generate_image`
- evidence tutor: default tutor tools plus `find` and `grep` for exact
  source/course-material search
- course-builder/admin: `pwd`, `ls`, `find`, `grep`, `read`, `write`,
  `edit`, `generate_image`, without learner-state tools such as
  `record_gate` or `remember`

High-level commands such as `append_section` and `update_section` are product
conveniences over those workspace primitives. In the storage layer they become
plain file operations: Markdown sections in `canvas/student/*.md`, interactive
component definitions in `canvas/components/*.yaml`, and generated media under
`canvas/student-assets/`. This keeps the model close to the same basic
capabilities that make coding agents useful, while the backend still enforces
tenant access, lecture unlocks, path safety, file-type limits, source
immutability, and auditability.

## Repository Layout

```txt
apps/api                 FastAPI backend and harness contracts
apps/latex-compiler      Isolated, bounded TeX-to-PDF preview service
apps/web                 React/Vite frontend
services/agent           Reserved extraction boundary; runtime is currently in API
packages/*               Reserved package boundaries; no runtime code yet
integrations/tuebingen   Integration boundary notes; adapter code is in API
docs                     Current architecture/operations docs and historical records
deploy                   Docker and self-hosting files
```

Start with the [documentation map](docs/README.md) to distinguish current
operating guidance from dated design/implementation records.
See [docs/media-discovery.md](docs/media-discovery.md) for the YouTube/media
pre-asset contract.
See [docs/course-ingestion-pipeline.md](docs/course-ingestion-pipeline.md) for
the upload, canvas planning/repair, professor review, and publication pipeline.
See [docs/workspaces.md](docs/workspaces.md) for filesystem-backed canvas and
learner storage.
See [docs/agent-tool-contracts.md](docs/agent-tool-contracts.md) for the
profile-scoped tutor tool contracts and UI activity tags.
See [docs/tenancy-security.md](docs/tenancy-security.md) for the tenant,
profile, and secure course-material upload contract.
See [docs/security-operations.md](docs/security-operations.md) for backup,
restore, incident, and remaining retention requirements.
See [security_best_practices_report.md](security_best_practices_report.md) for
the current evidence-backed pilot status and open production-approval gates.

## Product Changelog And Releases

LecturePilot keeps user-facing release notes in
[`apps/web/src/productChangelog.json`](apps/web/src/productChangelog.json). The
same bilingual source powers the in-app **What's new** page, the repository
[`CHANGELOG.md`](CHANGELOG.md), and GitHub Release notes. Entries describe what
changed for students and lecturers rather than repeating commit messages.

For a release:

1. Add the new version at the top of `productChangelog.json` and update the
   root, web, and API package versions.
2. Run `npm run changelog:render` and `npm run changelog:check`.
3. Merge the version change after CI passes, then tag that exact commit as
   `vX.Y.Z` and push the tag.

The tag-triggered release workflow validates that all versions and notes agree,
then publishes the matching bilingual GitHub Release. Mark a change with
`"feedbackDriven": true` when it directly implements user feedback.

## Local Development

Keep private professor/course files in `local-course-materials/`,
`course-materials/`, `lecture-materials/`, or `content/private/`. These paths
are gitignored on purpose; only sanitized examples and public fixtures should
be committed.

Course-material roots are intentionally private. By default, the API first
checks the repo-local ignored course-material folder used by the bundled demo
workspace. Set `LECTUREPILOT_COURSE_MATERIAL_ROOT` to point at another private
course checkout or upload workspace.

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e "apps/api[test,agent]"
export DATABASE_URL=postgresql://lecturepilot:lecturepilot-test@127.0.0.1:55432/lecturepilot_test
alembic -c apps/api/alembic.ini upgrade head
pytest apps/api/tests
uvicorn lecturepilot.app:app --app-dir apps/api/src --reload
```

TeX-only slide previews require the isolated local compiler. See
[docs/latex-compilation.md](docs/latex-compilation.md) for the run command and
the PDF-first fallback contract.

The full API suite requires a migrated PostgreSQL test database. CI provisions
Postgres 16 automatically; local development may use any disposable Postgres
instance at the exported URL.

Live Uni Tübingen login also needs the wrapper package in the API environment:

```bash
pip install -e "apps/api[tuebingen]"
```

Published wrapper support is pinned to `tue-api-wrapper==0.3.0`, which requires
the audited Pillow 12.3 security baseline. Local wrapper integration remains
useful for redacted development checks.

When developing both repos locally, use the editable wrapper checkout instead:

```bash
pip install -e ../tue-api-wrapper/package
```

Frontend:

```bash
npm install
npm run test --workspace apps/web
npm run dev --workspace apps/web
```

## Try The Chat

Run the API and web app in two terminals:

```bash
source .venv/bin/activate
export OPENAI_API_KEY=...
export LECTUREPILOT_MODEL=openai/gpt-5.6-luna
uvicorn lecturepilot.app:app --app-dir apps/api/src --reload
```

```bash
npm run dev --workspace apps/web
```

Open `http://127.0.0.1:5173`. In a development build, use **Preview local
demo**, select lecture 03, click the speech-bubble button on the right rail,
and ask for a Bayes concept check or a personalized example such as `Explain
this with a soccer example`.
The tutor calls the configured provider through the backend harness, marks the
quality gate as pending or passed, and focuses the relevant canvas block.

The deterministic `local-guided-preview` path remains available only as a
backend fixture for `local-preview-user` tests.

## Provider Setup

Copy `.env.example` to `.env` and set one provider key.

```bash
OPENAI_API_KEY=...
LECTUREPILOT_MODEL=openai/gpt-5.6-luna
LECTUREPILOT_IMAGE_PROVIDER=auto
GEMINI_IMAGE_MODEL=gemini-3.1-flash-image
```

The app is designed so provider routing sits behind the agent harness contract.
The frontend never calls model providers directly.

Infographic requests support Gemini, OpenRouter, and Hugging Face image
providers. `auto` prefers Gemini, then OpenRouter, then Hugging Face, and writes
the generated raster asset under the learner workspace. Without an image
provider key, infographic requests fail clearly instead of generating local SVG
placeholders.

Professor-side YouTube discovery is optional. Set `YOUTUBE_API_KEY` to enable
admin searches during course creation; approved selections are stored in the
private course-material workspace and render as inline video blocks in the
lesson canvas.

## Observability

Local tracing is disabled by default; production emits metadata-only JSON
spans. Configuration and privacy boundaries are documented in
[docs/observability.md](docs/observability.md).

## Historical Design Source

The original 2026-06-05 frontend direction is preserved in
[docs/glm-5.1-ui-design.md](docs/glm-5.1-ui-design.md). It is historical input,
not the current UI specification.

## Testing

```bash
npm run verify:fast
npm run verify:api
npm run verify:web
npm run verify:full
```

`verify:api` and `verify:web` are the component commands used by CI. All verify
commands enforce documentation links, formatting, zero lint warnings, and
`git diff --check`; the
full API suite requires the migrated disposable PostgreSQL database described
above.

Provider behavior is benchmarked separately from CI because real model calls are
non-deterministic and depend on configured keys. To compare whether candidate
models follow the tutor role, quality-gate policy, and structured output
contract, run:

```bash
python scripts/benchmark_gate_models.py \
  --model openai/gpt-5.6-luna \
  --model gemini/gemini-3.1-flash-lite
```

## License

Apache-2.0. See [LICENSE](LICENSE).
