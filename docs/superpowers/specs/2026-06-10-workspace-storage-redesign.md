# Workspace Storage Redesign

## Goal

LecturePilot needs a storage model that is easy to self-host, cheap to operate
for a university, and clear enough to seed into agent context. The tutor should
understand which files are official course evidence, which files are approved
canvas content, and which files are private learner memory or generated work.

## Storage Planes

The workspace is split into three durable planes plus one disposable cache.

```txt
.lecturepilot/
  users/
    <user-key>/
      profile.json
      memories/
        global.md
        preferences.json
      courses/
        <course-id>/
          progress.json
          memories/
            course.md
          lectures/
            <lecture-id>/
              attendance.json
              gates.json
              tutor-state.json
              canvas/
                student/*.md
                student-assets/*

  courses/
    <tenant-id>/
      <course-id>/
        course.json
        source/
          uploads/
          normalized/
          assets/
          source-index.json
        canvas/
          lectures/
            <lecture-id>/
              index.md
              sections/*.md
              assets/
        builder/
          drafts/
          review-state.json

  cache/
    pdf-previews/
    thumbnails/
    extracted-text/
```

Official source material belongs to the course. Learner memories belong to the
user. Personalized canvas additions belong to the user-course-lecture
intersection. Cached previews must be regeneratable.

## Agent Image

The agent acts inside a constrained image, not the host filesystem. Its initial
context should describe these roots:

- `course/source`: immutable professor-owned evidence, searched through source
  tools only.
- `course/canvas`: professor-approved base learning document.
- `user/memories`: cross-course learner profile and teaching preferences.
- `user/course/lecture`: attendance, progress, quality gates, tutor state, and
  private generated canvas overlays.
- `cache`: disposable previews and extracted text.

The agent should read and write through tools such as `search_course_source`,
`read_source_excerpt`, `read_user_memory`, `write_user_memory`,
`append_student_section`, `update_student_section`, `generate_infographic`,
`highlight_span`, and `record_gate_result`.

The agent must not freely traverse paths, mutate course sources, reveal future
lecture material, or infer authorization from browser-controlled ids.

## Images And Artifacts

Images should be persisted by ownership:

```txt
courses/<tenant>/<course>/source/assets/
  official professor assets

courses/<tenant>/<course>/canvas/lectures/<lecture>/assets/
  professor-approved generated or curated teaching assets

users/<user>/courses/<course>/lectures/<lecture>/canvas/student-assets/
  private learner-specific generated images

cache/thumbnails/
  disposable previews
```

Generated infographics should be raster images from a provider-backed
text-to-image tool. Do not use local SVG fallback generation as the learner
artifact path. SVG files may still exist as uploaded course source assets when
the backend policy allows them.

## Hosting Model

Local development can keep the logical image on disk. University deployments
should keep the same logical paths but back them with:

- Postgres for tenants, users, roles, enrollments, course manifests, progress,
  gates, retention metadata, file manifests, and audit logs.
- S3-compatible object storage such as MinIO for source files, approved canvas
  assets, generated learner artifacts, and previews.
- Optional Redis or a queue for long ingestion and image-generation jobs.

This avoids per-user containers and avoids duplicating large professor assets
into every learner workspace.

## Privacy And Quotas

Use pseudonymous user keys in object paths. Store raw university identifiers
only in protected profile/session records. A user deletion request should be
mostly satisfied by deleting `users/<user-key>/` plus database rows for that
user, without touching shared course material.

Recommended quota boundaries:

- Global learner memory: small text and JSON, normally under 10 MB.
- Per lecture learner overlay: Markdown plus generated assets.
- Per learner total generated artifacts: configurable, default 500 MB to 1 GB.
- Course source assets: tenant/course quotas, not learner quotas.
- Cache: size-limited and safe to evict.

## Migration Path

The current implementation stores student work under
`.lecturepilot/workspaces/students/<user>/courses/<course>/lectures/<lecture>/`.
Migration should introduce the new logical services first, then move existing
paths behind adapter methods.

1. Add typed path builders for user root, course root, lecture root, and cache.
2. Add user memory models and file APIs.
3. Move generated student assets and sections behind the new user lecture root.
4. Move course source/canvas resolution behind the new course root.
5. Keep a compatibility reader for old local workspaces during development.
6. Update AGENTS.md and docs whenever the agent-visible image changes.

## Success Checks

- The tutor can read cross-course user preferences before a turn.
- The tutor can update lecture gates and student canvas overlays without
  touching official course source files.
- A course source asset is stored once and referenced by many students.
- Deleting one user does not remove shared course source or approved canvas
  files.
- The same logical layout works with local filesystem storage and with
  Postgres plus object storage.
