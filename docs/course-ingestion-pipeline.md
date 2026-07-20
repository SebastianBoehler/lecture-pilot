# Course ingestion pipeline

Course creation is a professor-owned, source-grounded draft and publication
workflow. Deterministic parsing provides bounded evidence; the configured model
reorganizes that evidence into a learning canvas; students see nothing until an
owner publishes it.

```txt
create owned course
  -> upload files/folder tree
  -> index paths, types, sizes, and hashes
  -> infer and review lecture schedule
  -> assign source evidence per lecture
  -> generate private drafts
  -> repair, retry, and preview
  -> explicitly publish
```

## Storage and upload boundary

Professor files retain their relative folder structure under:

```txt
courses/<tenant>/<course>/source/uploads/
```

Derived PDFs, slide images, and other regeneratable artifacts live under
`source/normalized/` and are excluded from source discovery. The canonical
`source/source-index.json` records relative path, kind, byte size, SHA-256,
modification time, and status.

Accepted source kinds are LaTeX and its local support files, Markdown/text,
CSV/JSON, PDF, browser images/SVG, videos, Python, and notebooks. The backend:

- rejects absolute, hidden, traversal, unsupported, and oversized paths;
- streams multipart bodies in 1 MiB chunks to a private quarantine file;
- checks declared MIME and content signatures, including active-SVG rejection;
- computes SHA-256 while streaming; and
- atomically promotes without overwriting an existing target.

The request ceiling defaults to 600 MiB. Per-file limits are 2–10 MiB for text
formats, 20 MiB for images/notebooks, 100 MiB for PDF, and 500 MiB for video.
These are policy ceilings, not a claim that every maximum passed a production
load test. Malware scanning is not implemented.

Current initial-ingestion endpoints are:

```http
POST /admin/course-workspaces
POST /admin/courses/{course_id}/materials
GET  /courses/{course_id}/source-bundle
GET  /admin/courses/{course_id}/lecture-schedule
```

All `/admin` routes require the authenticated professor to own the exact
course. Development identity headers may be enabled locally, but are disabled
in production and are not part of the production contract.

For a private local Overleaf checkout, preserve the full tree except source
control metadata:

```bash
rsync -a --exclude '.git/' "$OVERLEAF_CHECKOUT/" \
  local-course-materials/<course-slug>/
```

## Schedule and lecture ownership

The server proposes a schedule from indexed filenames and content plus an
optional first date/count. The professor can rename, remove, add, and drag
lectures into the intended order before saving.

Folder and filename structure is evidence, not authority. Draft generation
selects files in this order:

1. saved per-lecture source-manifest paths;
2. the lecture's exact `material_path` and descendants of a unique lecture
   folder;
3. unambiguous lecture numbers in paths; and
4. recognized course-wide files such as a syllabus.

Same-named files in different lecture folders remain isolated. If nothing can
be assigned to a lecture, generation fails clearly rather than sending the
entire course to the model.

## Deterministic evidence adapters

| Kind                     | Current handling                                                                                                               |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| LaTeX                    | Import text/structure; use an authoritative matching PDF or compile a bounded handout preview in the isolated Tectonic service |
| Markdown/text            | Import bounded text and headings                                                                                               |
| PDF                      | Extract bounded text and render a representative sample of up to 20 pages                                                      |
| Python/notebook          | Import inert ordered Markdown/code; never execute code or retain outputs                                                       |
| Browser images/SVG/video | Preserve as source-backed media; optional JSON sidecars provide captions                                                       |
| CSV/JSON                 | Validate and index; no dedicated semantic canvas adapter yet                                                                   |

Notebook import reads at most 120 cells and 60,000 characters, ignores execution
counts, outputs, embedded image payloads, and remote images, and derives fenced
code language only from notebook metadata.

Matching uploaded PDFs remain authoritative. TeX-only previews use a
network-isolated, cached-package Tectonic service; unsupported workflows retain
the text canvas and a professor-facing warning. See
[latex-compilation.md](latex-compilation.md).

## Draft generation, status, and repair

The planner receives only the selected lecture evidence or a bounded digest. It
must produce typed sections whose blocks cite source references. Drafts are
stored privately as `index.md`, `sections/*.md`, assets, a learning map, and a
compiled API cache. Markdown is the editable source of truth.

Generation requests require a client-contract version and a 16–128 character
idempotency key. Private job records capture running/completed/failed state,
attempt number, heartbeat, and bounded error detail. The API keeps the task
independent of the browser connection, exposes status polling, uses a 15-minute
generation timeout, and permits a new attempt to claim an expired lease after
an interruption.

```http
POST /admin/courses/{course}/lectures/{lecture}/canvas/draft
GET  /admin/courses/{course}/lectures/{lecture}/canvas/draft/status
GET  /admin/courses/{course}/lectures/{lecture}/canvas/draft
POST /admin/courses/{course}/lectures/{lecture}/canvas/draft/repair
POST /admin/courses/{course}/lectures/{lecture}/canvas/publish
```

An actionable validation failure records its exact lecture, section/block,
source revision, invalid content, and compiler/validation constraint. **Fix with
AI** then asks the model for a constrained replacement of that target and
revalidates the complete draft, including the portable canvas-math contract. If no
exact target exists, repair regenerates the lecture draft with the recorded
failure context. A changed source revision invalidates surgical repair and
requires a fresh draft.

Publication atomically snapshots a valid draft, advances its publication
version, writes an audit event, and leaves the private draft intact. Learners
can read only published lectures that also pass access and date checks.

## Existing-course updates

Updates use a separate staging area. The server compares staged and live
indexes by relative path and SHA-256:

```txt
same path + same hash       -> unchanged
same path + different hash  -> changed
new path                    -> new
missing from staged upload  -> keep existing
```

The owner reviews ambiguous file-to-lecture assignments. Applying an update is
transactional across uploads, source index, lecture manifests, and schedule;
on failure, prior state is restored. Apply creates new private drafts for
affected lectures and never changes a published canvas by itself.

```http
POST   /admin/courses/{course}/updates
POST   /admin/courses/{course}/updates/{update}/materials
GET    /admin/courses/{course}/updates/{update}
POST   /admin/courses/{course}/updates/{update}/apply
DELETE /admin/courses/{course}/updates/{update}
```

## Optional media and generated assets

With `YOUTUBE_API_KEY`, an owner can search normalized YouTube candidates,
attach an approved candidate to an exact lecture section, list selections, or
remove them. Unapproved search results are never learner content. See
[media-discovery.md](media-discovery.md).

Generated course images remain private draft assets with source provenance
until publication. Learner-requested images are separate raster files in that
learner's overlay and count against the learner/provider quota.

Professor usage shows content-free token, request, and generated-image
aggregates for owned courses only. Prompt, response, source excerpt, filename,
and learner text are not stored in usage events. Institution-wide cost policy,
retention/deletion, and operator dashboards remain governance work; they do not
weaken the current owner-only authorization boundary.
