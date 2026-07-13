# Course Ingestion Pipeline

LecturePilot should treat deterministic source parsing as a bootstrap path, not
as the final course-authoring workflow. The intended professor/admin flow is:

```txt
clone/copy professor source bundle
  -> normalize files and build source manifest
  -> run large-context canvas planner
  -> create draft canvas sections and artifacts
  -> search optional YouTube candidates per section
  -> professor reviews, edits, approves, or rejects
  -> publish canvas for matched enrolled students
```

## Source Bundle

Course source files may be large and are not subject to the repository code-file
line limit. The codebase stays modular; uploaded professor files live under
`source/uploads/`, while rendered pages and other derived artifacts live under
`source/normalized/`. Derived files must never be rediscovered as professor
sources.

For Overleaf-backed courses, seed the course root from the full professor
checkout and exclude only Git metadata:

```bash
rsync -a --exclude '.git/' "$OVERLEAF_CHECKOUT/" local-course-materials/martius-ml/
```

The seed should preserve the professor's folder structure, including `images/`,
`videos/`, `code/`, `feedback/`, and lecture source files. The ingestion flow
then decides which files become cited canvas sources, optional artifacts, or
admin-only context.

Uploads update a canonical `source/source-index.json` manifest:

```json
{
  "course_id": "martius-ml",
  "schema_version": 1,
  "files": [
    {
      "path": "Lecture03/slides.pdf",
      "kind": "pdf",
      "size_bytes": 4820132,
      "sha256": "...",
      "modified_ns": 1783670400000000000,
      "status": "indexed"
    }
  ]
}
```

Supported source kinds are `latex`, `markdown`, `text`, `table`, `json`,
`pdf`, `image`, `svg`, `video`, `code`, and `notebook`.

The current API exposes the scanned bundle at:

```http
GET /courses/{course_id}/source-bundle
```

This returns indexed relative paths, file kinds, byte sizes, counts by kind,
and the course-material upload types accepted by backend policy. Refreshes
reuse hashes when size and modification time are unchanged.

Professor/admin uploads are staged through:

```http
POST /admin/courses/{course_id}/materials
X-Tenant-Id: tenant-tuebingen
X-User-Id: prof01
X-User-Role: professor
Content-Type: multipart/form-data
```

Form fields:

```txt
path=Lecture03-eng.tex
file=@Lecture03-eng.tex
```

The route checks the tenant role, rejects unsafe paths and unsupported file
types, streams the body in 1 MiB chunks, enforces the per-type size limit, and
atomically replaces the target. It computes SHA-256 during that same pass, so
indexing does not need to read a newly uploaded large video twice. A rejected
upload leaves no partial target behind. Production auth should replace the demo
headers with backend session context before this becomes user-facing.

## Lecture Ownership

Folder structure is evidence, not decoration. After a professor applies the
lecture schedule, draft generation selects only the files assigned to that
lecture. An exact `material_path` wins; a unique parent such as
`Lecture 02/` contributes its descendants; explicit lecture numbers in paths
are also matched. Course-wide files such as `syllabus.md` are shared. This
keeps same-named files such as `Lecture 01/slides.tex` and
`Lecture 02/slides.tex` isolated while retaining their full paths in source
references.

If no indexed source can be assigned to the requested lecture, generation
fails clearly instead of silently feeding the whole course to the model.

## Current Format Boundary

“Schema-free” currently means the professor may preserve folders and filenames;
it does not yet mean that every accepted binary format receives equivalent
semantic extraction.

| Kind                  | Current deterministic handling                                            |
| --------------------- | ------------------------------------------------------------------------- |
| LaTeX, Markdown, text | Text and structure imported locally                                       |
| PDF                   | Text extracted and pages rendered locally, up to 20 pages per draft       |
| Python, notebook      | Markdown and code imported locally as ordered, fenced Canvas content      |
| Images, SVG, videos   | Preserved as source-backed media; optional JSON sidecars provide captions |
| CSV, JSON             | Safely uploaded and indexed; semantic canvas extraction is still pending  |

Current per-file limits are 2–10 MiB for textual formats, 20 MiB for images and
notebooks, 100 MiB for PDFs, and 500 MiB for videos. The total request ceiling
defaults to 600 MiB. These are safety defaults, not evidence that every maximum
has passed a production load test.

Notebook import never executes code. It imports at most 120 cells and 60,000
characters, preserves Markdown/code order, derives the code-fence language from
notebook metadata, and ignores execution counts, cell outputs, and inline image
payloads or remote image fetches. Standalone Python files use the same inert
fenced-code representation. This keeps the path deterministic, safe, and free
of model or sandbox costs.

The next resource-efficient adapters should parse CSV/JSON locally, probe video
metadata with `ffprobe`, and make audio transcription an explicit opt-in job
with duration and cost quotas. They should not add a new provider credential:
use the configured OpenAI-compatible provider only where local extraction
cannot recover semantics.

## LLM Canvas Planner

The planner receives the selected lecture evidence or a structured digest, not
the full course bundle. It outputs a draft canvas, not final published material.

Expected planner output:

```json
{
  "title": "Bayesian Decision Theory",
  "sections": [
    {
      "id": "bayes-formula",
      "title": "Bayes formula and conditional probability",
      "learning_goals": ["Explain posterior as updated belief"],
      "blocks": [
        { "type": "paragraph", "source_refs": ["Lecture03-eng.tex#frames=6-9"] },
        { "type": "math", "source_refs": ["Lecture03-eng.tex#frame=7"] },
        { "type": "asset", "source_refs": ["images/Ch3/Venn_C-X_1.pdf"] },
        { "type": "checkpoint", "text": "Explain posterior, likelihood, and evidence." },
        {
          "type": "quiz",
          "text": "Which term normalizes Bayes' rule?",
          "items": ["Prior", "Evidence"]
        }
      ]
    }
  ]
}
```

The model may reorganize slides into better learning sections, but every block
must cite source material. It should not introduce unsupported topics.

Published drafts are written as `index.md` plus `sections/*.md`, not as hand
edited JSON. The current parser supports narrative Markdown paragraphs, image
references, YouTube links, Markdown tables, math fences, callouts, checkpoints,
and quiz blocks. JSON is still used as the model interchange and API cache, but
Markdown remains the editable canvas source.

## Optional Media Discovery

Professors can enable external media discovery during course creation:

```json
{
  "include_youtube_candidates": true,
  "max_candidates_per_section": 8
}
```

The pipeline should derive search queries from approved section goals, collect
metadata/transcripts where permitted, and stage candidates for review. Nothing
is published until a professor approves it.

The current implementation exposes the approval slice:

```http
GET /admin/courses/{course_id}/media/youtube/search?q={query}
POST /admin/courses/{course_id}/lectures/{lecture_id}/media/youtube
```

The search endpoint returns normalized candidates. The include endpoint writes
the approved selection to the private course-material root under
`canvas/media/` and the canvas reader merges it into the selected lesson
section as a `video` block.

## Optional Generated Artifacts

The pipeline may generate infographics, diagrams, code examples, or exercises
from the source-grounded section plan. Generated artifacts are stored as draft
course assets with provenance:

```json
{
  "kind": "infographic",
  "path": "canvas/assets/bayes-flow.png",
  "derived_from": ["Lecture03-eng.tex#frames=6-9"],
  "review_status": "needs_review"
}
```

Professor approval is required before generated assets become part of the base
course canvas. Student-specific generated content remains in the learner
workspace overlay.

## Review States

Course material moves through explicit states:

```txt
uploaded -> indexed -> draft_canvas -> needs_review -> approved -> published
```

Students only see `published` lectures whose lecture date has already passed.
Drafts, rejected candidates, and unapproved generated artifacts stay in the
admin workspace.

## Future Platform Admin Governance

Professors already have a separate **Usage** view for their own courses. The
backend records content-free provider events with the workload, model, input,
output, cached, reasoning, and total token counts returned by the provider.
The view also aggregates tutor turns and generated learner images. Recording
starts with the deployment of this schema and does not estimate or backfill
older requests. Course ownership is enforced before aggregation; prompts,
responses, learner text, source excerpts, and filenames are never stored in
the usage event.

The ingestion and cost-control roadmap should add a distinct platform-admin
account above professor accounts. This is not part of the first ingestion
milestone, but the authorization model should leave room for an admin to:

- approve, suspend, and audit professor accounts;
- review course-level and professor-level API, storage, and processing usage;
- set institution, professor, and course quotas or budget ceilings;
- review provider usage, retries, cache hits, and estimated cost over time;
- inspect failed or unusually expensive ingestion jobs without seeing learner
  or course content by default; and
- manage institution-wide retention, deletion, and allowed-format policy.

Professor approval and budget enforcement must remain backend-authoritative.
Browser-supplied roles, tenant ids, or quota values are never
accepted as authority.

### Privacy-Restricted MLflow Operations View

The backend already has optional MLflow observability around agent turns, model
calls, tool spans, canvas writes, and quality-gate decisions. It is disabled by
default, and `LECTUREPILOT_TRACE_CONTENT=metadata` is the production-safe
starting point. The platform-admin dashboard can build an aggregate operations
view from this data instead of introducing another telemetry provider.

The dashboard should allowlist only operational fields such as span type, tool
name, success state, normalized error code, latency, model/provider, retry and
cache counts, and pseudonymous institution/course/professor keys. It must not
store or display prompts, completions, learner text, tool arguments or results,
source excerpts or filenames, raw user identifiers, emails, IP addresses,
authentication data, or unrestricted exception messages. Before production,
the current raw tool error output should become a finite error category.

Prefer a backend-owned aggregate dashboard over exposing MLflow directly. A
deep link to an individual trace should be available only to explicitly
authorized operators, use an opaque trace id, remain behind the same protected
network and access controls, and be audited. `redacted` or `full` tracing must
never power the normal admin dashboard; full content is restricted to an
explicit, time-limited private debugging session with short retention.
