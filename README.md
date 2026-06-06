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
- Provider capability checks with OpenRouter GLM 5.1 as the default model.
- Local preview tutor that leads a deterministic quality-gate loop without a
  provider key.
- React/Vite frontend with dashboard and focused lesson workspace.
- TUE API login form backed by the local FastAPI API and `tue-api-wrapper`.
- Tenant/profile policy foundation for professors, tutors, and students.
- Light and dark mode.
- Backend and frontend tests.
- CI, Dockerfiles, and Compose starter.

Provider-backed tutor turns for real authenticated users intentionally fail with
a clear error until a real API key is configured.

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
See [docs/workspaces.md](docs/workspaces.md) for filesystem-backed canvas and
learner storage.
See [docs/tenancy-security.md](docs/tenancy-security.md) for the tenant,
profile, and secure course-material upload contract.

## Local Development

Keep private professor/course files in `local-course-materials/`,
`course-materials/`, `lecture-materials/`, or `content/private/`. These paths
are gitignored on purpose; only sanitized examples and public fixtures should
be committed.

For the Martius demo slice, point `LECTUREPILOT_COURSE_MATERIAL_ROOT` at the
private Overleaf checkout containing `Lecture03-eng.tex`. If the variable is
empty, the API searches the local Tübingen course folder and then falls back to
`local-course-materials/martius-ml`.

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e "apps/api[test,agent]"
pytest apps/api/tests
uvicorn lecturepilot.app:app --app-dir apps/api/src --reload
```

Live Uni Tübingen login also needs the wrapper package in the API environment:

```bash
pip install -e "apps/api[tuebingen]"
```

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
export OPENROUTER_API_KEY=...
export LECTUREPILOT_MODEL=openrouter/z-ai/glm-5.1
uvicorn lecturepilot.app:app --app-dir apps/api/src --reload
```

```bash
npm run dev --workspace apps/web
```

Open `http://127.0.0.1:5173`, use **Preview local demo**, select lecture 03,
click the speech-bubble button on the right rail, and ask for a Bayes concept
check or a personalized example such as `Explain this with a soccer example`.
The preview tutor leads the conversation, persists new canvas sections in the
ignored student workspace, marks the quality gate as pending or passed, and
focuses or highlights the relevant canvas block.

For provider-backed turns, sign in with your Uni credentials through the local
backend after configuring a provider key.

## Provider Setup

Copy `.env.example` to `.env` and set one provider key.

```bash
OPENROUTER_API_KEY=...
LECTUREPILOT_MODEL=openrouter/z-ai/glm-5.1
```

The app is designed so provider routing sits behind the agent harness contract.
The frontend never calls model providers directly.

## Design Source

The first frontend direction was generated with OpenRouter model
`z-ai/glm-5.1` and saved in [docs/glm-5.1-ui-design.md](docs/glm-5.1-ui-design.md).

## Testing

```bash
pytest apps/api/tests
npm run test --workspace apps/web
npm run build --workspace apps/web
```

## License

Apache-2.0. See [LICENSE](LICENSE).
