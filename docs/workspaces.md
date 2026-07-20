# Workspace storage

LecturePilot stores one professor-owned course source/canvas and private
learner overlays. The default local root is `.lecturepilot/`; production
Compose mounts the same logical layout at `/app/storage` on a persistent named
volume.

```txt
<workspace-root>/
  courses/<tenant-id>/<course-id>/
    source/
      uploads/
      normalized/
      source-index.json
    canvas/lectures/<lecture-id>/
      index.md
      sections/*.md
      assets/
      publication.json
      learning-map.json
    canvas-drafts/lectures/<lecture-id>/latest/
    builder/
      generations/<lecture-id>/*.json
      repairs/<lecture-id>.json
      source-manifests/<lecture-id>.json
      updates/<update-id>/
    canvas/media/
    course.json

  users/<hashed-user-id>/
    memories/
      global.md
      preferences.json
      memory-trace.jsonl
    courses/<course-id>/
      progress.json
      memories/
        course.md
        memory-trace.jsonl
      lectures/<lecture-id>/
        attendance.json
        gates.json
        tutor-state.json
        canvas/
          index.md
          sections/*.md
          student/*.md
          components/*.yaml
          student-assets/*
        canvas.json

  previews/professors/<hashed-preview-id>/...
```

The exact set of files is created lazily; absence is normal before a course,
draft, learner state, or optional feature exists.

## Durable storage boundary

Postgres is authoritative for users, sessions, roles, ownership, enrollments,
audit events, and quotas. The workspace volume is authoritative for course
files, generated derivatives, Markdown canvases, generation state, and learner
overlays. A recovery operation must treat both as one matched unit.

Production does not currently use S3-compatible object storage. Protected
course and learner assets are served through authenticated API routes. An
object-storage adapter would also require short-lived signed delivery and must
preserve all capability, ownership, and path checks.

## Professor source and builder state

Uploaded material lives only under the owned course's `source/uploads/` root.
The canonical index records relative paths, types, sizes, hashes, and
modification metadata. Rendered PDF pages and TeX-compiled previews live in
`source/normalized/` and are excluded from source discovery.

Private builder state includes:

- lecture-to-source manifests;
- staged incremental updates and their analysis;
- idempotent generation records with actor and request-key hashes;
- targeted-repair provenance tied to a source revision; and
- the latest private draft for each lecture.

Publication atomically copies a valid draft into the shared course canvas and
increments `publication.json`. Original source files remain immutable evidence.
Students never read drafts, staged updates, generation errors, or repair
records.

Local sanitized demos may set `LECTUREPILOT_COURSE_MATERIAL_ROOT`; the seeded
course can read that legacy source/canvas layout. Uploaded production courses
must have an explicitly published course canvas. New writes use the current
course and `users/` layout.

## Learner workspace

`StorageLayout.user_key` hashes the authenticated user ID before it becomes a
directory name. Raw university usernames and browser-supplied user IDs do not
select filesystem roots.

Cross-course teaching preferences and notes live under `memories/`. Course
memory is separate so course-specific observations do not bleed into another
subject. Each `memory-trace.jsonl` entry records scope, course, lecture, tool,
note, and any preference change for provenance.

Course `progress.json` holds exam-readiness attempts and revision state.
Per-lecture state holds attendance, gates, coaching state, and the canvas
overlay. Agent-created Markdown goes to `canvas/student/*.md`;
interactive definitions go to `canvas/components/*.yaml`; provider-generated
raster images go to `canvas/student-assets/`. `canvas.json` is a compiled API
cache, never the editable source of truth.

The reader can import old `workspaces/students/.../canvas.json` or legacy asset
paths for migration compatibility. It does not write new learner state there.
Learner reset removes only the authenticated learner's selected course state.

## Professor learner preview

A course owner can enter learner mode without impersonating a student. The
preview uses the same attendance, canvas, tutor, memory, and image contracts but
stores them under a pseudonymous `previews/professors/` root derived from the
owner and course.

Preview state is excluded from learner/cohort analytics. Model and image usage
still belongs to the professor account. Resetting a preview cannot address or
delete a real learner workspace.

## Canvas Markdown

One section file is one stable teaching unit. The parser supports:

- paragraphs with light Markdown and inline math;
- raw LaTeX display fences using ` ```math `;
- course assets through `asset:relative/path`;
- authenticated learner asset URLs;
- approved YouTube links;
- Markdown tables;
- callouts, checkpoints, and quizzes; and
- explicit block comments for stable focus/highlight IDs.

Example:

````md
<!-- block id="risk-equation" type="math" -->

```math
R(a_i\mid x)=\sum_j L(a_i\mid \omega_j)P(\omega_j\mid x)
```

:::checkpoint Risk gate
Explain why changing a loss term can move the decision threshold.
:::

:::quiz Retrieval check
Which quantity directly changes the expected-risk decision?

- Posterior probability
- Slide number
- Font size
  :::
````

Generated canvas math is intentionally more portable than arbitrary professor
TeX: it accepts a KaTeX-compatible command/environment subset, rejects preamble
macros and prose in math blocks, and gives targeted repair an exact block when
possible. This restriction applies to the learning canvas, not to the isolated
Tectonic slide-preview compiler.

## Agent-visible roots

The model never receives host filesystem access. Typed capabilities expose only
the roots needed for the active profile:

```txt
/course/source/uploads   read-only professor evidence
/course/canvas           read-only published canvas
/lecture/canvas          current learner overlay
/user/memories           current learner global memory
/user/course/memories    current learner course memory
/user/profile.json       current learner profile
```

Tutor writes are restricted to learner Markdown/components/assets and memory.
Course-builder writes are restricted to its course-authoring workspace and do
not gain learner memory or gate tools. See
[agent-tool-contracts.md](agent-tool-contracts.md).

## File policy

Generated learner files are limited to Markdown (5 MiB), text/JSON/YAML (2
MiB), raster images (20 MiB), and SVG (2 MiB). Course material has separate
per-type limits up to 100 MiB for PDF and 500 MiB for video.

Logical and HTTP access rejects absolute/hidden/traversal paths, unsupported
types, oversized content, symbolic-link escape, and hard links. Professor
uploads additionally use signature/MIME validation, quarantine, and atomic
promotion. Durable quotas and audit events are implemented; malware scanning,
automated retention/deletion, and object storage are not.
