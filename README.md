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
harness. The first target integration is University of Tübingen via
[`tue-api-wrapper`](https://github.com/SebastianBoehler/tue-api-wrapper).

## Preview

<p align="center">
  <img
    alt="LecturePilot lesson canvas showing a Bayesian Decision Theory lecture with source-backed content and workspace tools"
    src="docs/assets/lecturepilot-lesson-ui.jpg"
    width="900"
  />
</p>

## What It Builds Toward

- Login through university credentials.
- Fetch courses and timetables from the university backend.
- Show only lectures that already happened.
- Ask whether the learner attended.
- Load official lecture material from LaTeX/PDF/Markdown sources.
- Render a focused lesson canvas.
- Discover curated external media as workspace pre-assets.
- Let a text-only agent highlight, explain, quiz, and save progress.

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
- Light and dark mode.
- Backend and frontend tests.
- CI, Dockerfiles, and Compose starter.

Provider-backed tutor turns intentionally fail with a clear error until a real
API key is configured.

## Agent Harness Direction

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

This direction matches current agent frameworks: agents are configured with
instructions, tools, state, and runtime guardrails; MCP-style tools expose
external systems through controlled roots; durable runtimes add persistence,
human review, and traceability around those tool calls. Optional observability
such as MLflow/OpenTelemetry should wrap these low-level tool spans rather than
being built into the student-facing UI first.

## Repository Layout

```txt
apps/api                 FastAPI backend and harness contracts
apps/web                 React/Vite frontend
services/agent           Agent runtime notes and future ADK/LiteLLM service
packages/workspace       Workspace package placeholder
packages/course          Course package placeholder
packages/agent-harness   Harness package placeholder
integrations/tuebingen   TUE API wrapper integration placeholder
docs                     Architecture and design notes
deploy                   Docker and self-hosting files
```

See [docs/media-discovery.md](docs/media-discovery.md) for the YouTube/media
pre-asset contract.
See [docs/course-ingestion-pipeline.md](docs/course-ingestion-pipeline.md) for
the long-context LLM upload, canvas planning, and professor approval pipeline.
See [docs/workspaces.md](docs/workspaces.md) for filesystem-backed canvas and
learner storage.
See [docs/agent-tool-contracts.md](docs/agent-tool-contracts.md) for the
profile-scoped tutor tool contracts and UI activity tags.
See [docs/tenancy-security.md](docs/tenancy-security.md) for the tenant,
profile, and secure course-material upload contract.
See [docs/security-operations.md](docs/security-operations.md) for backup,
restore, incident, and remaining retention requirements.
See [security_best_practices_report.md](security_best_practices_report.md) for
the current pre-deployment decision and open blockers.

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
export GEMINI_API_KEY=...
export LECTUREPILOT_MODEL=gemini/gemini-3.1-flash-lite
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
GEMINI_API_KEY=...
LECTUREPILOT_MODEL=gemini/gemini-3.1-flash-lite
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

## Optional Observability

LecturePilot ships with a no-op observability layer by default. To trace agent
turns, model calls, low-level workspace tools, canvas writes, and quality-gate
decisions into a self-hosted MLflow tracking server, install the optional
backend dependency and enable the backend:

```bash
pip install -e "apps/api[observability]"
export LECTUREPILOT_OBSERVABILITY=mlflow
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
export MLFLOW_EXPERIMENT=lecturepilot-dev
```

Trace content defaults to metadata only. Set
`LECTUREPILOT_TRACE_CONTENT=redacted` to add hashed prompt/response payloads, or
`LECTUREPILOT_TRACE_CONTENT=full` only in local/private debugging sessions where
course and student text may be stored in the tracing backend.

## Design Source

The first frontend direction was generated with OpenRouter model
`z-ai/glm-5.1` and saved in [docs/glm-5.1-ui-design.md](docs/glm-5.1-ui-design.md).

## Testing

```bash
pytest apps/api/tests
npm run test --workspace apps/web
npm run build --workspace apps/web
```

Provider behavior is benchmarked separately from CI because real model calls are
non-deterministic and depend on configured keys. To compare whether candidate
models follow the tutor role, quality-gate policy, and structured output
contract, run:

```bash
python scripts/benchmark_gate_models.py \
  --model gemini/gemini-3.1-flash-lite \
  --model gemini/gemini-3.5-flash
```

## License

Apache-2.0. See [LICENSE](LICENSE).
