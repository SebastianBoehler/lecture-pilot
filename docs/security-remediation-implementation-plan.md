# LecturePilot Security Remediation Implementation Plan

Status: local implementation complete; live release blocked by the items listed below<br>
Prepared: 2026-07-10<br>
Baseline: `main` at `01608fe`<br>
Source findings: `security_best_practices_report.md`

## Agreed product and security decisions

- Alma authenticates the university identity and supplies the active account role. A non-student
  role creates a professor candidate, but only platform approval grants the LecturePilot professor
  role.
- The first successful university login creates or updates a database-backed user.
- A platform administrator approves a user as a professor once. The administrator does not assign
  each professor-created course.
- A professor verified by Alma creates a course and becomes its owner in the same database transaction.
- LecturePilot cannot enumerate the university-wide Alma or ILIAS course catalog. An approved
  professor creates a platform course using its title and term without selecting an upstream row.
- On student login, the student's own Alma and ILIAS memberships are matched conservatively by
  normalized exact title plus term. A unique match stores source, stable upstream ID, and term as
  durable enrollment evidence; an ambiguous match grants no access.
- A professor has no tenant-wide course access. In the first release, only the professor who creates
  a course can manage it; delegated tutor or co-instructor management is deferred.
- Professors see only aggregate course analytics. They cannot read or mutate a learner's canvas,
  chat, memory, generated files, readiness history, or agent session.
- A platform administrator can approve and disable accounts but cannot inspect course or learner
  content through ordinary administration routes.
- The tutor remains fully capable inside its authorized virtual workspace. The boundary limits
  which roots exist, not which normal file-navigation tools it may use inside those roots.
- No live VM deployment happens until the final deployment gate is approved.

## Confirmed matching and analytics decisions

- [x] Use both Alma and ILIAS enrollment evidence because university programs enroll through
      different systems.
- [x] Use Alma `unitId` and ILIAS course `ref_id`/`goto.php/crs/<id>` as the stable identifiers
      exposed by the current wrapper records. Keep a real cross-account fixture check in the staging
      gate because representative student values across both enrollment systems remain unverified.
- [x] Do not impose a minimum analytics cohort size. Return aggregate data when events exist and an
      explicit no-data result when none exist; never expose learner-level records.
- [x] Defer co-instructor and tutor invitations. The course creator is the only manager in this
      release.
- [x] Defer platform course discovery, join requests, and professor approval of join requests.

## Target authorization model

| Scope    | Capability                                               | Holder                     |
| -------- | -------------------------------------------------------- | -------------------------- |
| Platform | approve/disable professor accounts                       | `platform_admin`           |
| Platform | create a course                                          | approved `professor`       |
| Course   | manage source, lectures, publishing, aggregate analytics | `course_owner`             |
| Course   | learn from unlocked material                             | active `course_enrollment` |
| Learner  | canvas, chat, memory, files, agent turns, reset          | that learner only          |

The tenant-level professor flag means “may create a course.” It never means “may access every
course.” Course capability comes from `courses.owner_user_id`. Platform administration and course
content access remain separate. A future migration may add delegated staff without broadening the
initial owner-only rule.

## Phase 0 — Freeze contracts with failing security tests

- [x] Add a route inventory that classifies every endpoint as public, self-service, platform-admin,
      course-owner/editor, aggregate-analytics, or enrolled-student.
- [x] Add failing tests proving an approved but unrelated professor receives `403` for another
      course's admin, source, publish, media, deletion, and analytics routes.
- [x] Add failing tests proving professors and platform admins receive `403` for learner canvases,
      assets, agent turns, quiz submission on behalf of a learner, reset, chat, and memory.
- [x] Add failing tests proving learner identity always comes from the session, not `user_id` in a
      path, query, or body.
- [x] Add failing tests for duplicate course titles, renamed courses, cross-term collisions, and
      upstream candidates without a stable identifier.
- [x] Record the final matrix in `docs/tenancy-security.md` and remove the current statement that
      professors/tutors may review private learner progress.

Gate 0:

- [x] The desired access matrix is reviewed and the new negative tests fail for the expected reason.
- [ ] The stable Alma and ILIAS identity contract is verified with representative records.

## Phase 1 — Add the Postgres persistence foundation

Use SQLAlchemy 2, Psycopg 3, and Alembic. Keep Pydantic API schemas separate from persistence models,
and keep each new module below the repository's 300-line soft limit.

- [x] Add pinned `sqlalchemy`, `psycopg`, and `alembic` dependencies and regenerate the API lockfile.
- [x] Add `database.py`, request-scoped transaction handling, migration configuration, and an
      explicit migration command. Production startup must fail if the schema is missing or stale;
      the web process must not silently create tables.
- [x] Create UUID-keyed tables: `users`, `external_identities`, `tenant_memberships`,
      `sessions`, `courses`, `course_external_refs`, `course_enrollments`, and
      `audit_events`.
- [x] Store external usernames only in the protected identity table. Use internal UUIDs and
      pseudonymous storage keys elsewhere.
- [x] Add unique constraints for external identity, enrollment, and
      `(tenant, source, external_course_id, term)` course links; make the non-null course owner a
      foreign key to an Alma-verified professor.
- [x] Add status/timestamp fields for approval, revocation, enrollment sync, soft course archival,
      and audit provenance.
- [x] Add PostgreSQL to the API CI job and run migrations before tests. Do not use SQLite as proof of
      PostgreSQL constraint or transaction behavior.

Gate 1:

- [x] `alembic upgrade head`, downgrade/upgrade on an empty test database, and schema drift check pass.
- [ ] Concurrent duplicate identity, approval, course-link, and owner creation tests pass.
- [x] The application fails closed when `DATABASE_URL` is absent in production.

## Phase 2 — Database-backed login, sessions, and Alma role authority

- [x] Refactor `TuebingenCourseAdapter` to return authenticated identity, the server-reported Alma
      role profile, and upstream assignments as data only. Never accept a browser-selected role or
      persist the submitted password.
- [x] Use one university login for students and professors. The active `student` Alma role remains a
      student; any other active Alma role grants professor access. Persist the raw active and
      available roles for audit.
- [x] Remove the separate local professor credential flow. Alma is the only login path, and the
      submitted university password is never persisted or returned.
- [x] Create the university identity, tenant membership, and role audit event atomically.
- [x] Replace the signed claim cookie with a random opaque session identifier. Store only its hash in
      `sessions`; rotate on login/privilege change, enforce expiry, and support immediate revocation.
- [x] Make `request_context` load the current enabled user, membership, and session from the database.
      Remove roles and course IDs as self-contained cookie authority.
- [x] Add `GET /me` with the server-verified account type and Alma role.
- [x] Keep a platform-admin endpoint to disable accounts without granting course or learner access.
- [x] Add a one-time operator CLI to bootstrap the first platform admin by exact external identity.
      Every bootstrap and approval action writes an audit event.
- [x] Update the UI with one university entry path and remove demo access from production builds.

Gate 2:

- [x] Student and Alma-professor fixtures produce database-derived roles only; approval revokes the
      pending session, and a fresh professor login receives the approved role.
- [x] University login responses contain account display data and approval status but no credential.
- [ ] Logout, password-independent session revocation, privilege change, fixation rotation, expiry,
      and concurrent-session tests pass.
- [x] Logs, responses, browser storage, and cookies contain no university or professor password and
      no JavaScript-readable session token. Browser role/course metadata is display state only and
      never backend authority.

## Phase 3 — Professor-owned course creation and login-time upstream matching

- [x] Define an `ExternalCourseCandidate` login contract with source, stable external ID, term,
      number, title, organization, instructor metadata, and display URL. Discard upstream rows that
      do not expose a stable ID.
- [x] Generate an opaque LecturePilot course UUID at professor-created course creation; no upstream
      catalog selector or platform administrator is involved.
- [x] Match only a student's own login memberships against active platform courses using normalized
      exact title plus term. Require exactly one match; zero or multiple matches grant no access.
- [x] After a unique title/term match, persist `(tenant, source, external_course_id, term)` in
      `course_external_refs` and use that stable link on subsequent logins even if display metadata
      changes.
- [x] Upsert active `course_enrollments` from both Alma and ILIAS evidence. A failed source refresh
      preserves evidence from that source; a successful refresh marks missing evidence inactive.
- [x] Keep platform course search and join-request workflows out of this release.

Gate 3:

- [x] Two identically named platform courses in one term are treated as ambiguous and do not grant
      enrollment; different terms and stable source IDs do not collide.
- [x] Renaming a display title does not change ownership or student enrollment after stable binding.
- [x] The creator can manage the new course; another professor cannot see or mutate it.
- [x] A student's enrolled courses are resolved from database links, not session claims or title
      slugs after the initial unique match.

## Phase 4 — Enforce course ownership and learner privacy everywhere

- [x] Replace `require_course_manager` and tenant-wide teaching shortcuts with centralized
      `require_platform_admin`, `require_professor`, `require_course_capability`,
      `require_enrollment`, and `require_self` dependencies.
- [x] Scope every lookup by tenant and opaque resource ID before reading files or database records.
- [x] Convert all admin routes in `app.py`, `course_canvas_routes.py`, `admin_media_routes.py`,
      `analytics_routes.py`, and `course_deletion.py` to owner/editor capability checks.
- [x] Remove learner `user_id` from `AgentTurnInput`, quiz inputs, canvas requests, reset requests,
      and frontend APIs. Derive it from `request_context` at the route boundary.
- [x] Make workspace assets self-only. Remove professor/tutor access to individual learner assets,
      canvases, chats, memories, progress, and agent execution.
- [x] Expose only aggregate analytics to course owners. Return real aggregate totals, slices, weak
      sections, and readiness metrics when data exists; never return pseudonymous learner keys or
      generated values when no data exists.
- [x] Keep raw analytics events internal to the aggregation service and add privacy-safe audit events
      for course administration and aggregate report access.
- [x] Archive instead of immediately deleting a course; require owner authorization and a separate,
      audited retention job for physical deletion.

Gate 4:

- [x] The generated route/role/ownership matrix passes for unauthenticated, student, unrelated
      professor, owner, and platform-admin identities.
- [x] No professor-facing route accepts a learner ID or returns learner-level data.
- [ ] IDOR tests cover guessed tenant, course, lecture, asset, publication, and learner identifiers.

## Phase 5 — Make the agent filesystem a real capability boundary

- [x] Introduce a single `WorkspaceCapability` manifest and `WorkspaceFS` service. Agent tools receive
      logical roots and capabilities, never arbitrary `Path` values or the host storage root.
- [x] Build learner-turn capabilities only after session, enrollment, lecture-unlock, and ownership
      checks. Include the learner's own memory/overlay plus authorized published/unlocked course
      canvas and source references; exclude other learners, courses, drafts, and future lectures.
- [x] Give the course-builder agent a separate owner-authorized manifest containing that course's
      source/draft roots and no learner roots.
- [x] Route `pwd`, `ls`, `find`, `grep`, `read`, `write`, `edit`, image placement, source scanning, and
      asset serving through `WorkspaceFS`; remove direct traversal from agent executors.
- [x] Reject every symlink and require each opened component to remain under its capability root.
      Use descriptor-relative, no-follow opens for local storage to avoid check/open races.
- [ ] Mount course sources/canvas read-only and learner overlays writable in production. Keep the API
      process and provider SDKs from receiving broader host mounts than required.
- [x] Preserve full navigation within the manifest: recursive list/find/grep/read remain available,
      and writes remain available throughout the explicitly writable learner roots.
- [ ] Add object-storage adapters later behind the same capability interface; object keys must be
      server-generated and tenant/course/user scoped.

Gate 5:

- [x] Nested file and directory symlink, absolute path, `..`, Unicode normalization, hidden path,
      hard-link where applicable, and symlink-swap tests cannot escape any root.
- [ ] Property tests exercise every tool against every root and verify read-only/write boundaries.
- [x] A normal tutor can still discover and use every file in its intended virtual workspace.
- [x] The agent never receives a host path in prompts, tool results, errors, traces, or API responses.

## Phase 6 — Close request, dependency, and assessment blockers

- [x] Add session-bound CSRF tokens plus strict Origin and Fetch Metadata validation for every
      cookie-authenticated state-changing route. Centralize the frontend CSRF header in `api.ts`.
- [x] Upgrade and relock `python-multipart` to a compatible patched version at or above `0.0.30` and
      rerun crafted multipart/urlencoded denial-of-service regressions.
- [x] Split readiness DTOs so pre-attempt responses contain no answer index or rubric. Load canonical
      answers only during server-side scoring.
- [x] Remove absolute storage paths and unnecessary staff identity from public response models.

Gate 6:

- [x] Every mutation rejects missing/wrong CSRF tokens and untrusted same-site sibling origins.
- [ ] `pip-audit` has no reachable high-severity runtime finding.
- [x] Browser/API tests prove readiness answers are absent before submission.

## Phase 7 — Bound expensive and untrusted operations

- [x] Add a server-side model allowlist by role/use case; remove arbitrary browser model names as
      provider authority.
- [x] Add durable per-user/course spend, token, image, concurrency, and daily limits in Postgres.
- [x] Stream uploads to quarantine; validate size and magic/MIME before publication; generate storage
      names server-side and reject symlinks/archives/polyglots outside policy.
- [x] Move PDF/image processing to a bounded worker with page, pixel, CPU, memory, disk, and timeout
      limits. Serve risky originals as attachments or from an isolated origin.

Gate 7:

- [ ] Disallowed, over-budget, duplicate-concurrent, oversized, malformed, and decompression-bomb
      requests fail before provider or expensive parser work.
- [x] Quotas remain correct across multiple API workers and process restarts.

## Phase 8 — Deployment, migration, and release gate

- [x] Add same-origin `/api` and protected-asset proxying behind HTTPS; keep API and Postgres on an
      internal network and expose only the approved public web ports.
- [x] Run API and workers as non-root with dropped capabilities, read-only root filesystems, bounded
      resources, explicit trusted hosts/proxies, and production-only secret requirements.
- [ ] Point `LECTUREPILOT_WORKSPACE_ROOT` at the persisted volume and migrate existing file manifests
      to opaque database IDs without copying learner data into course roots.
- [ ] Add backup, restore, retention, account deletion, session revocation, audit review, and incident
      runbooks. Complete the privacy notice and provider/subprocessor inventory.
- [ ] Run migrations and smoke checks in a disposable staging environment first. Do not deploy the
      reviewed VM until the user separately approves live deployment.

Final gate:

- [x] API tests, web tests, quality, production build, dependency scans, secret scan, container scan,
      route matrix, agent confinement suite, and `git diff --check` pass.
- [ ] Live staging verifies TLS, cookies, CSRF, headers, Host/Origin rejection, public ports, non-root
      runtime, enrollment sync, professor approval, course matching, isolation, and backup restore.
- [ ] `security_best_practices_report.md` is re-reviewed and every public-hosting blocker is closed or
      explicitly accepted by the user before any VM deployment.

Current blockers are representative cross-account student Alma/ILIAS identifiers, disposable
hosted staging and restore verification, and approval of retention, deletion, privacy, and
provider/subprocessor operations. These are intentionally not marked complete or silently accepted.

## Planned implementation checkpoints

Implement and review one checkpoint at a time:

1. `feat(auth): add database identity and session foundation`
2. `feat(auth): add audited professor approval flow`
3. `feat(courses): link professor-owned courses to university records`
4. `fix(authz): enforce course ownership and learner-only workspaces`
5. `fix(agent): enforce capability-scoped symlink-safe workspaces`
6. `fix(security): add csrf and close dependency and readiness leaks`
7. `fix(security): enforce quotas and bounded upload processing`
8. `chore(deploy): harden staging runtime and persistence`

Each checkpoint starts with its negative regression tests, contains its migration and documentation
updates, and must pass the narrow tests before the full CI-aligned suite. Do not combine checkpoints
into one large commit.
