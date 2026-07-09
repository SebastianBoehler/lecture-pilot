# LecturePilot Security Review

Date: 2026-07-09

## Executive Summary

Follow-up changes addressed the critical and high findings in this report.
Deployment auth fails closed outside explicit local/test environments, Compose
forces session auth with a required secret, course/workspace asset routes require
auth, course enrollment is enforced, dynamic lecture dates are gated, and the
tutor no longer exposes the global material root. Additional hardening now adds
request body limits, security headers, production docs disabling, dependency
locks, API rate limits, and HTTPOnly cookie login sessions.

Positive controls observed: centralized route auth dependencies, path-aware
upload validation, constrained learner write roots, React markdown without raw
HTML plugins, KaTeX `trust: false`, production-mode session auth tests, locked
install paths, and app-level throttling for login/chat/paid endpoints.

Scope: FastAPI backend, React/Vite frontend, Docker/Compose deployment files,
auth/assets/path-policy tests, tracked secret scan, and a second read-only
code-review pass.

## Critical Findings

### C-1. Deployment Defaults Can Leave Forged Header Auth Enabled

**Rule:** FASTAPI-AUTH-001

**Location:** `apps/api/src/lecturepilot/session_auth.py:28`,
`apps/api/src/lecturepilot/api_auth.py:19`, `deploy/compose.yml:6`,
`.env.example:1`

**Impact:** If the checked-in Compose flow is exposed without extra production
env, a network user can forge `X-User-Role: professor` and call
professor/admin routes.

**Status:** Fixed in follow-up changes by making env-less auth default to
session mode, rejecting dev-header auth outside local/test envs, and forcing
production session auth in `deploy/compose.yml`.

### C-2. Course And Learner Asset Routes Are Public

**Rule:** FASTAPI-FILES-001, FASTAPI-AUTHZ-001

**Location:** `apps/api/src/lecturepilot/app.py:253`,
`apps/api/src/lecturepilot/app.py:277`,
`apps/api/src/lecturepilot/storage_layout.py:22`

**Impact:** Anyone with a URL can fetch professor course media or learner-owned
generated assets without a session, tenant check, enrollment check, or learner
ownership check.

**Status:** Fixed in follow-up changes by moving asset routes into
`asset_routes.py`, adding `request_context`, enforcing same-tenant checks for
course assets, and enforcing learner ownership or teaching role for workspace
assets. The frontend now renders protected media through authenticated blob
fetches rather than raw bearer-less `<img>` / `<video>` requests.

## High Findings

### H-1. Same-Tenant Access Is Treated As Course Enrollment

**Rule:** FASTAPI-AUTHZ-001

**Location:** `apps/api/src/lecturepilot/app.py:105`,
`apps/api/src/lecturepilot/course_canvas_routes.py:120`,
`apps/api/src/lecturepilot/tenancy.py:54`

**Impact:** Any valid student in the tenant can discover and access published
course workspaces if they know or can list the course id, even if they are not
enrolled.

**Evidence before fix:** `/courses` returns all tenant courses after only
`require_same_tenant()` (`app.py:105-111`). Stored workspace lectures are
returned as `unlocked: True` for every lecture (`app.py:138-145`). Canvas access
uses `require_learner_workspace_access()`, which checks same tenant and
self/teaching-role visibility but not enrollment (`course_canvas_routes.py:120-145`;
`tenancy.py:54-64`). `docs/tenancy-security.md:94-99` still lists enrollment
tables as required before production.

**Status:** Fixed with signed/dev `course_ids` in `TenantContext` plus shared
`course_access` checks across course listing, lectures, canvas, readiness,
analytics, agent, and asset routes.

### H-2. Lecture Date Unlock Is Not Enforced On Published Dynamic Courses

**Rule:** FASTAPI-AUTHZ-001

**Location:** `apps/api/src/lecturepilot/app.py:138`,
`apps/api/src/lecturepilot/course_canvas_routes.py:132`

**Impact:** Future lecture material can be exposed early if it is published or
if a student guesses a lecture id.

**Evidence before fix:** For stored workspaces, `/courses/{course_id}/lectures` returns
every lecture with `unlocked: True` (`app.py:138-145`). The canvas route checks
publication state before reading the document, but not `lecture.date <= today`
(`course_canvas_routes.py:132-145`).

**Status:** Fixed by resolving lectures through server-side schedule data and
denying future lectures to non-review roles across learner course/lecture routes.

### H-3. Tutor Read Roots Can Expose The Whole Material Root

**Rule:** FASTAPI-AUTHZ-001

**Location:** `apps/api/src/lecturepilot/agent_tool_workspace.py:17`,
`apps/api/src/lecturepilot/agent_tool_schemas.py:8`,
`apps/api/src/lecturepilot/canvas_workspace_config.py:15`

**Impact:** If the configured material root contains multiple courses or future
lectures, a student prompt can induce the tutor to search/read unrelated private
material and summarize it.

**Evidence before fix:** The agent root map exposes `/course/materials` as
`canvas_workspace.material_root` (`agent_tool_workspace.py:17-27`). The default
tutor profile includes `read`, and evidence mode adds `find` and `grep`
(`agent_tool_schemas.py:8-34`). The material root can be any configured
`LECTUREPILOT_COURSE_MATERIAL_ROOT` (`canvas_workspace_config.py:15-18`).

**Status:** Fixed by removing global `/course/materials` from learner tutor roots
and updating the tool-contract docs and security regression coverage.

## Medium Findings

### M-1. Risky Upload Formats Are Served Same-Origin Without Production Controls

**Rule:** FASTAPI-UPLOAD-001, FASTAPI-FILES-001

**Location:** `apps/api/src/lecturepilot/workspace.py:36`,
`apps/api/src/lecturepilot/latex_canvas_text.py:173`,
`apps/api/src/lecturepilot/app.py:275`

**Impact:** Malicious or compromised professor material can become active
same-origin content when opened directly, especially SVG. Malware scanning and
content-disarm are also absent.

**Evidence:** Professor uploads allow SVG, PDFs, videos, Python, and notebooks
(`workspace.py:36-55`). Browser asset suffixes include `.svg` and `.pdf`
(`latex_canvas_text.py:173`), and matching assets are served inline by
`FileResponse` (`app.py:253-275`). `docs/tenancy-security.md:58-63` already
calls out SVG/video MIME handling, sanitization or attachment serving, and
signed URLs.

**Fix:** Serve risky uploads as attachments or from an isolated asset origin,
rasterize/sanitize SVG and PDF previews before inline rendering, and add MIME
sniffing plus malware scanning before publication.

### M-2. Large Uploads Are Read Fully Into Memory Before Size Enforcement

**Rule:** FASTAPI-LIMITS-001

**Location:** `apps/api/src/lecturepilot/app.py:224`,
`apps/api/src/lecturepilot/workspace.py:42`

**Impact:** A professor account, or anyone in dev-header mode, can force large
request bodies into API memory.

**Evidence:** `upload_course_material()` calls `payload = await file.read()`
before checking `len(payload)` (`app.py:224-244`). The policy permits PDFs up to
100 MB and videos up to 500 MB (`workspace.py:42-55`). No reverse-proxy body
limit is visible in `deploy/compose.yml`.

**Status:** Mitigated with `RequestBodyLimitMiddleware` and
`LECTUREPILOT_MAX_REQUEST_BYTES` defaulting to a generous 600 MiB cap. Compose
sets the same default. Accepted uploads still read into memory after the request
passes the cap, so streaming upload storage remains a future improvement rather
than a release blocker for the current test deployment.

### M-3. Video URL Fallbacks Lack A Shared URL Allowlist

**Rule:** REACT-URL-001

**Location:** `apps/web/src/CanvasBlocks.tsx:190`,
`apps/web/src/WorkspaceFilesPanel.tsx:80`,
`apps/api/src/lecturepilot/canvas_models.py:24`

**Impact:** A bad stored media URL can become a clickable unsafe navigation
sink.

**Evidence:** `CanvasBlock.asset_url` is only a bounded string
(`canvas_models.py:24-25`). Non-YouTube, non-native video fallbacks render
`<a href={block.asset_url}>` and `<a href={url}>` without the `safeHref()` check
used by `MathText.SafeLink` (`CanvasBlocks.tsx:190-207`;
`WorkspaceFilesPanel.tsx:80-85`). Current generated model sections do not allow
arbitrary video blocks, but authored/imported canvas paths can still carry
external media URLs.

**Fix:** Centralize a URL sanitizer/allowlist for all `href`, `src`, iframe, and
video contexts. Allow only same-origin relative URLs plus explicit YouTube HTTPS
origins for video links.

### M-4. Security Headers And OpenAPI Exposure Are Not Controlled In Repo

**Rule:** FASTAPI-HEADERS-001, FASTAPI-OPENAPI-001, REACT-HEADERS-001

**Location:** `apps/api/src/lecturepilot/app.py:58`,
`apps/api/src/lecturepilot/app.py:71`, `apps/web/Dockerfile:11`

**Impact:** Public deployments expose API surface details and lack browser
defense-in-depth unless an external proxy provides headers.

**Evidence:** The API constructs `FastAPI(...)` with default docs/openapi URLs
(`app.py:58`). The only visible middleware is CORS (`app.py:71-77`). The web
container uses default nginx without checked-in CSP, frame, nosniff, or
referrer-policy headers (`apps/web/Dockerfile:11-13`).

**Status:** Fixed in repo. `SecurityHeadersMiddleware` now adds CSP, nosniff,
frame-deny, no-referrer, and permissions-policy headers. HSTS is available via
`LECTUREPILOT_HSTS_ENABLED=true` but intentionally opt-in to avoid accidental
local/domain lockout. `LECTUREPILOT_ENV=production` disables FastAPI docs,
OpenAPI, and ReDoc. The web nginx config also sets CSP and related browser
headers for static assets. A real deployed-header check is still required after
deployment.

## Low Findings And Verification Gaps

### L-1. Dependency Builds Are Not Reproducible

**Rule:** REACT-SUPPLY-001, FASTAPI-SUPPLY-001

**Location:** `.github/workflows/ci.yml:39`, `apps/web/Dockerfile:6`,
`apps/api/pyproject.toml:7`, `apps/api/Dockerfile:9`

**Evidence before fix:** There is no root package manager lockfile. CI and web Docker use
`npm install` (`.github/workflows/ci.yml:39-40`; `apps/web/Dockerfile:6-9`).
Python deployment dependencies use broad lower bounds (`pyproject.toml:7-33`)
and `pip install -e` (`apps/api/Dockerfile:9`).

**Status:** Fixed for current repo builds. `package-lock.json` is committed, CI
and the web Docker image use `npm ci`, direct API dependencies are pinned, and
`apps/api/requirements.lock` constrains API installs. `npm audit --omit=dev`
reported 0 production vulnerabilities.

### L-2. Login, Chat, And Paid Endpoint Rate Limiting Is Not Visible

**Rule:** FASTAPI-AUTH-001

**Location:** `apps/api/src/lecturepilot/app.py:113`

**Evidence before fix:** `/auth/login` forwards username/password to the Tuebingen adapter
and returns 401/503, but no app-level rate limiting is visible
(`app.py:113-128`).

**Status:** Fixed for single-process/self-hosted test deployment. `RateLimitMiddleware`
now applies fixed-window limits to `/auth/login`, `/agent/turn`,
`/agent/turn/stream`, course canvas draft generation, lecture scheduling,
exam-readiness attempts, and YouTube media search. Defaults are intentionally
generous and configurable through `LECTUREPILOT_RATE_LIMIT_*`. A distributed
limiter should replace this if the API is scaled across workers or nodes.

### L-3. Session Tokens Are JavaScript-Readable

**Rule:** REACT-AUTH-001

**Location:** `apps/web/src/loginSessionStorage.ts:31`,
`apps/api/src/lecturepilot/session_auth.py:39`

**Evidence before fix:** The frontend stores bearer access tokens in `sessionStorage`
(`loginSessionStorage.ts:31-35`). Default token lifetime is 480 minutes
(`session_auth.py:39`).

**Status:** Fixed for real login. `/auth/login` now sets an HTTPOnly SameSite
session cookie and returns no browser-readable access token. Frontend fetches
include credentials and persist only tokenless session metadata. Bearer/dev
headers remain only for explicit local/demo flows and tests.

## Verification Performed

```bash
pytest apps/api/tests -q
npm run test --workspace apps/web
npm run build --workspace apps/web
npm run lint:api
npm run lint:web
npm ci --ignore-scripts --dry-run
npm audit --omit=dev
python -m pip install --dry-run -c apps/api/requirements.lock -e "apps/api[test,agent]"
npx prettier --check <touched web/config files>
python -m ruff format --check <touched api files>
git diff --check
```

Result: API `234 passed`; web `72 passed`; web build passed; API lint passed;
web lint had 6 existing hook-dependency warnings; npm production audit reported
0 vulnerabilities; npm lockfile dry-run passed with local Node 23.11.0 engine
warnings; pip lock dry-run passed; formatting and diff whitespace passed.

No full dynamic penetration test or deployed-header check was performed.

## Release Recommendation

The critical/high release blockers from this review are fixed. For student and
first-lecture testing, the remaining security work is production hardening:
sanitized/isolated handling for risky uploaded formats, a shared URL allowlist
for every media/link sink, a deployed-header/cookie verification pass, and a
distributed rate limiter before multi-node scaling.
