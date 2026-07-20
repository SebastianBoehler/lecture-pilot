# LecturePilot API

The FastAPI application is LecturePilot's policy and runtime boundary. The web
client never talks directly to university or model providers.

Implemented responsibilities include:

- Alma-backed identity synchronization, Postgres sessions, CSRF, roles,
  ownership, enrollment, audit events, and quotas;
- course creation, upload/index, schedule generation, staged updates, private
  canvas drafts, targeted AI repair, publication, and aggregate usage;
- server-enforced lecture access and private learner/preview workspaces;
- the LiteLLM-backed tutor and course-builder harness with constrained tools;
- source parsing, PDF rendering, and the client for the isolated Tectonic
  compiler service; and
- health/readiness, metadata-only observability, and production preflight.

Run from the repository root using the setup and verification commands in
[`../../README.md`](../../README.md). Production topology and required settings
are documented in [`../../docs/self-hosting.md`](../../docs/self-hosting.md).
