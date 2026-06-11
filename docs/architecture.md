# Architecture

LecturePilot separates the product app from the agent runtime.

```txt
Web app
  login, dashboard, lecture selection, focused canvas

Backend API
  auth sessions, tenant context, course discovery, unlock policy, workspace API

Agent harness
  model routing, tool contract, canvas commands, progress events

Workspace store
  read-only course seed plus private learner overlay
```

## Core Principle

The interface gives structure. The backend enforces rules. The workspace stores
learning state. The agent operates inside that sandbox.

## Access Control

Lecture access is not prompt-enforced. The backend checks:

```txt
profile belongs to tenant
profile has course membership
lecture.date <= today
```

The agent receives only already-authorized course material ids.

Professor and tutor capabilities are tenant-local. Course creation, material
uploads, and progress review must be authorized against the active tenant before
any course or file lookup happens.

## Workspace Model

The agent sees a filesystem-like workspace, but writes go through a typed API.

Allowed generated files:

- `.md`
- `.txt`
- `.json`
- `.png`
- `.svg`

Blocked by default:

- executables
- archives
- arbitrary binaries
- hidden files
- parent path traversal
- oversized files

Local development can use folders. Production should back the workspace with
Postgres metadata and S3-compatible object storage such as MinIO.

See [tenancy-security.md](tenancy-security.md) for the professor/student role
model, tenant isolation rules, and secure material-upload contract.

## Low-Level Agent Tools

The tutor should eventually use a small set of general workspace tools instead
of many product-specific commands. The model should learn one environment: a
course/user filesystem image plus a rendered canvas.

Core tools:

- `list_workspace`, `read_file`, `write_file`, `patch_file`
- `search_course_source`, `read_source_excerpt`
- `focus_canvas`, `highlight_span`, `scroll_to`
- `generate_image`, `discover_media`
- `record_gate`, `read_memory`, `write_memory`

`append_section` and `update_section` remain useful compatibility commands, but
they should compile down to file writes inside `canvas/student/*.md`,
`canvas/components/*.yaml`, and `canvas/student-assets/`. The backend owns path
validation, file-size limits, course-source read-only rules, lecture unlocks,
and tenant/profile authorization.

This keeps the harness close to coding-agent ergonomics: the model reasons over
files and navigation, while the application turns those edits into a safe
student-facing learning interface.

## Provider Model

The app depends on a harness contract, not a provider SDK.

```txt
AgentTurnInput -> AgentTurnResult
```

`ProviderRegistry` validates that the selected model has a configured key and
the capabilities required by the turn. The current default is
`gemini/gemini-2.5-flash-lite`, and the selected model can be changed with
`LECTUREPILOT_MODEL`.

## Future ADK Runtime

The first real agent implementation should add an ADK/LiteLLM runtime behind
the existing `LecturePilotHarness.run_turn` contract. It should emit:

- text response
- canvas commands
- artifact commands
- progress events
- tool/model events

No UI code should depend directly on ADK.
