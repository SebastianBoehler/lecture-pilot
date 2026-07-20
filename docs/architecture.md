# Architecture

LecturePilot is a same-origin web application with backend-enforced teaching,
authorization, workspace, and provider policy. The deployed runtime is the
checked-in Compose topology; the reserved `packages/` and `services/agent/`
directories are not separate runtime components.

```txt
browser
  -> Caddy HTTPS gateway
       -> React/Vite static web app
       -> /api -> FastAPI application
                    -> Postgres
                    -> persisted /app/storage volume
                    -> internal Tectonic compiler
                    -> university and model/image providers
```

Only Caddy publishes ports 80 and 443. Postgres, the API, web container, and
compiler remain on Compose networks. Provider and university credentials exist
only in the API environment; the compiler receives no secrets and has no
external network.

## Backend policy boundary

The browser supplies requests, never authority. The API derives the current
user, tenant, role, and visible courses from an opaque database session. It
enforces:

- the active server-reported Alma role (`student` maps to learner; any other
  active role maps to professor);
- exact course ownership for professor administration;
- current enrollment or allowed course visibility for learners;
- publication and `lecture.date <= today` before learner access; and
- self-only learner canvas, memory, assets, readiness, analytics events, and
  reset operations.

Development headers exist only when explicitly enabled outside production.
Production disables them and OpenAPI, requires exact Host/Origin lists, and
protects cookie-authenticated mutations with CSRF and Fetch Metadata checks.
See [tenancy-security.md](tenancy-security.md).

## Persistence and workspaces

Postgres stores identities, memberships, opaque session/CSRF hashes, courses,
ownership, enrollment evidence, audit events, and usage quotas. The persisted
application volume stores professor source material, normalized derivatives,
private drafts, published Markdown canvases, generation records, and learner
overlays.

The logical filesystem image separates:

- immutable professor uploads under `courses/<tenant>/<course>/source`;
- private builder state and drafts under the course root;
- published course canvases shared by authorized learners;
- pseudonymous learner memory and per-lecture overlays under
  `users/<hashed-user-id>`; and
- isolated professor preview state under `previews/professors`.

Agent and HTTP file access goes through typed, capability-scoped,
descriptor-safe paths. Hidden paths, traversal, unsafe links, hard links,
unsupported types, and oversized operations are rejected. Production currently
uses the persistent volume; an S3-compatible adapter and signed URLs are not
implemented. See [workspaces.md](workspaces.md).

## Course creation and publication

The professor workflow is implemented as:

```txt
create owned course
  -> upload files or folder tree
  -> index by relative path and SHA-256
  -> infer and reorder lecture schedule
  -> assign evidence per lecture
  -> generate private canvas drafts
  -> repair a failed draft or exact invalid block when actionable
  -> preview and explicitly publish
```

Uploads stream through quarantine, validate type/size/content, and promote
atomically. Existing courses use a staged update workspace: changed files and
lecture assignments are reviewed before an atomic apply, and published canvases
are not replaced until the professor publishes new drafts.

Canvas generation uses idempotency keys, private job records, heartbeats, a
bounded lease, and status polling. Closing the browser does not make the
in-process generation task depend on the tab; after interruption or process
loss, a stale lease can be claimed for another attempt. Repair validates that
the failed draft still refers to the current source revision and uses a
surgical block replacement when the failure contains an exact target. See
[course-ingestion-pipeline.md](course-ingestion-pipeline.md).

## Canvas and agent runtime

Published course Markdown is the official learning surface. Learner-specific
notes, components, and generated images form a private overlay; `canvas.json`
is a compiled cache, not the editable source of truth.

`LecturePilotHarness.run_turn` is the provider-independent contract. The
current provider-backed runtime runs inside FastAPI through LiteLLM. It selects
the configured server-allowlisted model, requests structured output, and may
execute profile-scoped tools over logical roots:

- tutor: known-path reads, learner writes/edits, canvas navigation, gate and
  memory records, and generated raster images;
- evidence tutor: tutor tools plus bounded `find` and `grep`; and
- course builder: source search/read plus course-draft write/edit and image
  generation, without learner gate or memory tools.

High-level append/update canvas commands materialize through the same learner
Markdown/component storage. Tool results are structured, returned to the model
on failure, and shown as UI activity only when a real operation occurred. The
deterministic local preview remains a test/development fixture, not the
production tutor. See [agent-tool-contracts.md](agent-tool-contracts.md).

## Source rendering

Uploaded matching PDFs are authoritative for slide previews. When a lecture is
TeX-only, the API bundles only its indexed dependencies and sends a bounded
archive to the internal Tectonic service. Runtime package downloads and shell
escape are disabled. A compilation failure keeps text evidence usable and
surfaces a professor warning; it never runs TeX in the API process. See
[latex-compilation.md](latex-compilation.md).

## Observability and recovery

Production records metadata-only request, auth, generation, model, and tool
events in rotating JSONL logs. Prompt, response, source, filename, credential,
and raw learner content are excluded. Optional MLflow tracing is for explicitly
configured private environments.

Postgres and `/app/storage` form one recovery unit. Operators must back up and
restore matching versions together. The implementation does not replace the
outstanding restore rehearsal, retention/deletion policy, or privacy approval;
see [self-hosting.md](self-hosting.md) and
[security-operations.md](security-operations.md).
