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
line limit. The codebase stays modular; uploaded lecture sources, PDFs, images,
videos, code notebooks, and generated previews live in gitignored
course-material roots.

For Overleaf-backed courses, seed the course root from the full professor
checkout and exclude only Git metadata:

```bash
rsync -a --exclude '.git/' "$OVERLEAF_CHECKOUT/" local-course-materials/martius-ml/
```

The seed should preserve the professor's folder structure, including `images/`,
`videos/`, `code/`, `feedback/`, and lecture source files. The ingestion flow
then decides which files become cited canvas sources, optional artifacts, or
admin-only context.

Each upload should produce a manifest:

```json
{
  "course_id": "martius-ml",
  "lecture_id": "lecture-03",
  "sources": [
    { "path": "sources/Lecture03-eng.tex", "kind": "latex" },
    { "path": "sources/slides.pdf", "kind": "pdf" },
    { "path": "images/Ch3/Venn_C-X_1.pdf", "kind": "pdf" },
    { "path": "videos/MontyPythonSpam.mp4", "kind": "video" },
    { "path": "code/bayesian-decision/ROC_AUC_demo.ipynb", "kind": "notebook" }
  ]
}
```

Supported source kinds are `latex`, `markdown`, `text`, `table`, `json`,
`pdf`, `image`, `svg`, `video`, `code`, and `notebook`.

The current API exposes the scanned bundle at:

```http
GET /courses/{course_id}/source-bundle
```

This returns relative paths, file kinds, byte sizes, counts by kind, and the
course-material upload types accepted by backend policy. It is intended as the
read-only input for a professor/admin course creation view.

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

The route is intentionally narrow: it checks the tenant role, rejects unsafe
paths and unsupported file types, writes into the configured course-material
root, and then the source-bundle scanner and canvas importer can pick the file
up. Production auth should replace the demo headers with backend session
context before this becomes user-facing.

## LLM Canvas Planner

The planner should use a long-context model such as Gemini with the full source
bundle or a structured source digest. It outputs a draft canvas, not final
published material.

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
        { "type": "quiz", "text": "Which term normalizes Bayes' rule?", "items": ["Prior", "Evidence"] }
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
