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

## Provider Model

The app depends on a harness contract, not a provider SDK.

```txt
AgentTurnInput -> AgentTurnResult
```

`ProviderRegistry` validates that the selected model has a configured key and
the capabilities required by the turn. The current default is
`openrouter/z-ai/glm-5.1`.

## Future ADK Runtime

The first real agent implementation should add an ADK/LiteLLM runtime behind
the existing `LecturePilotHarness.run_turn` contract. It should emit:

- text response
- canvas commands
- artifact commands
- progress events
- tool/model events

No UI code should depend directly on ADK.
