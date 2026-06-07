# Tenancy And Profile Security

LecturePilot needs two profile surfaces:

- Professor and tutor profiles for tenant-owned course management, material
  uploads, lecture publishing, and progress review.
- Student profiles for Uni Tübingen login, enrolled-course access, attendance,
  tutor sessions, and private progress storage.

This follows the same broad role split as
[`martius-lab/ai-tutor`](https://github.com/martius-lab/ai-tutor), where tutors
and admins have elevated review roles, but LecturePilot should make tenant
membership explicit because it will host multiple courses and potentially
multiple university groups.

## Roles

```txt
tenant_admin   manages tenant settings, professors, and offboarding
professor      creates courses, uploads official material, publishes lectures
tutor          reviews student progress and submitted conversations
student        learns inside enrolled courses and owns private progress
```

Roles are tenant-local. A professor in one tenant must not receive professor
permissions in another tenant unless that second membership exists.

## Security Rules

- Derive tenant context from the authenticated session, not from editable
  request headers, query parameters, or frontend state.
- Deny by default. Every course, progress, upload, and file-read operation must
  pass an explicit tenant and role policy check.
- Scope all resource lookups by tenant and resource id. Do not fetch by resource
  id alone.
- Use opaque public ids for persistent tenants, courses, lectures, files, and
  users. Avoid sequential ids for externally reachable resources.
- Prefix cache keys and object-storage paths with a hashed tenant prefix so
  tenant names are not exposed through storage keys.
- Keep official course source material read-only after publication. Store
  learner notes, generated artifacts, progress, and quiz results in a private
  per-learner overlay.
- Record audit events for login, tenant selection, course creation, material
  upload, publication, progress review, and administrative changes.

## Professor Material Uploads

Uploads must be treated as untrusted input even when they come from professors:

1. Require a professor or tenant_admin role in the course tenant.
2. Validate path, extension, and size before storage.
3. Generate storage keys server-side under the tenant prefix.
4. Store files outside the web app container and serve through authorization
   checks or short-lived signed URLs.
5. Run MIME sniffing, antivirus, and content-disarm hooks before publication.
6. Serve risky formats as attachments unless they are converted or sanitized.

The current code implements the first policy layer for typed uploads:
TeX, Markdown/text, CSV/JSON, PDFs, images including SVG/GIF, videos, Python
source files, and notebooks. Code and notebooks are course source artifacts;
they must be reviewed and displayed as inert files unless a separate sandboxed
execution path is built. SVG and video files require careful MIME handling,
sanitization or attachment serving, and signed URLs in production.

## Student Access

Student access starts from Uni Tübingen login and then maps the authenticated
identity to tenant membership plus enrolled courses. The frontend may display
available courses, but the backend must still enforce:

```txt
same tenant
course enrollment or teaching role
lecture.date <= today
material belongs to course
private progress belongs to learner, professor, tutor, or tenant_admin
```

The agent never receives a raw tenant id from the browser as authority. It gets
material ids only after the backend has resolved tenant membership, course
access, lecture unlock status, and file policy.

## Implementation Status

Implemented now:

- `TenantRole`, `TenantMembership`, and `UserProfile` models.
- `TenantContext` derived from profile membership.
- Professor/tenant_admin course-management and upload gates.
- Tutor/professor/tenant_admin progress-review gate.
- Hashed tenant prefixes for storage and cache keys.
- Separate course-material upload policy.

Still required before production:

- Persistent tenants, profiles, course ownership, and enrollment tables.
- Session/JWT validation and tenant context dependency on protected routers.
- Professor course-management UI and API routes.
- Object storage with signed URL generation and malware scanning.
- Tenant-specific quotas, audit logs, offboarding, and retention controls.
