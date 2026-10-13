# Course updates

A professor updates a running course by uploading changed or new material on the
update page. The update must change only the lectures whose material changed:
unchanged lectures keep their approved goals, drafts and publications, changed
lectures ask whether to keep or regenerate their goals, and new lectures get
goals proposed automatically. Nothing is drafted or published without the
professor.

## Lecture-local source revisions

Every approval, draft binding, review, publication, repair record and generation
job is bound to the lecture's source revision
(`sources/lecture_source_revision.py`, re-exported as
`authoring.course_canvas_repairs.lecture_source_revision`). The revision is a
SHA-256 over exactly these inputs:

- the lecture's own schedule entry: id, title, date and material path;
- the files selected for the lecture: every route that is lecture-specific to it
  or course-wide (before a course has any routing: its source manifest), with the
  file's current SHA-256 from the source index (`missing` when the file left the
  index); and
- the route of each of those files: kind, role and lecture id.

Other lectures, unrelated uploads, excluded files, unrelated routes, the routing's
`confirmed` flag and its course-wide `source_revision` are not inputs. A change to
a course-wide file changes every lecture that uses it; pruning unused uploads
changes nothing. Readers compute it from stored files without parsing sources.

### Legacy alias migration

Before this definition, the revision also hashed the whole course's provenance
(every lecture's schedule entry, the full source index and the full routing, mapped
through the storage-only cleanup receipt
`builder/source-retention-provenance.json`). Stored bindings are never rewritten.
Instead, the storage migration `2026-10-lecture-source-alias`
(`migrations_storage/storage_migration_lecture_source_alias.py`) records, once,
for each lecture with a source manifest whose legacy revision is referenced by a
stored file of the course (`builder/`, `canvas/`, `canvas-drafts/`):

```json
// builder/source-manifests/<lecture-id>.alias.json
{ "local": "<lecture-local revision>", "legacy": "<revision returned before>" }
```

While a lecture's computed local revision equals `local`, the runtime returns
`legacy`, so every approval, draft and publication that was current at deploy
stays current. Once the lecture's own inputs change, the local revision is
returned and those bindings are stale; identical inputs map back to `legacy`.
Lectures whose legacy revision nothing refers to get no alias. Existing aliases
are never rewritten. The legacy formula lives only in the migration module.

Inspect before deploying (read-only dry run):

```bash
python -m lecturepilot.storage_migrations --root /path/to/storage
```

## Applying an update

```http
POST   /admin/courses/{course}/updates
POST   /admin/courses/{course}/updates/{update}/materials
GET    /admin/courses/{course}/updates/{update}
POST   /admin/courses/{course}/updates/{update}/apply
DELETE /admin/courses/{course}/updates/{update}
```

The analysis compares staged and live files by path and SHA-256 and proposes a
lecture for each new or changed file. New lecture titles come from the LaTeX
`\title` (or Markdown front-matter `title`) without a leading "Lecture NN:" /
"Vorlesung NN:", then document metadata such as `pdftitle`, then the first
non-administrative heading (`courses/lecture_title.py`).

The review assigns every applied file to one existing lecture, a new lecture, all
existing lectures, or ignores it (ignored files are not applied). Apply is one
transaction over uploads, source index, schedule, routing and manifests
(`courses/course_update_apply.py`):

- **Routing on apply** (`courses/course_update_routing.py`). When the routing was
  confirmed for the sources before the update, apply extends it without a model
  call: a file selected for one lecture becomes lecture-specific, a file selected
  for several or all existing lectures becomes course-wide (a changed course-wide
  file assigned to every existing lecture stays course-wide), and all other
  confirmed routes are kept. The routing is confirmed for the updated sources
  through the ordinary `confirm_source_routing`, so its validation and revision
  update are identical to a manual confirmation. Applied routes never exclude a
  file and the earlier confirmation already pruned unused uploads, so nothing is
  pruned. Every lecture's manifest is rewritten from the new routing.
- When the routing was not confirmed (or covers files outside the update), the
  result reports `routing: "needs_review"` and the professor confirms the routing
  as usual before anything can be drafted.
- **New lectures** (`new_lecture_ids`) get learning goals proposed in the
  background when the routing is confirmed
  (`learning_design/learning_goal_proposal_jobs.py`). The request writes a durable
  `builder/goal-proposals/<lecture-id>.json` marker and returns; one asyncio task
  proposes goals lecture by lecture through the same workflow as
  `POST .../practice-design/intent/proposal` (`learning_goal_proposal_run.py`),
  holding a shared background-generation slot and renewing a 60-second lease. An
  expired lease (for example after a restart) no longer reports `proposing`;
  failures are recorded and the professor proposes again from goal review.
- **Changed lectures** keep their goals untouched; the approved goals report
  `stale`. Drafts are never started automatically.

The apply response adds `new_lecture_ids` and `routing` to the earlier
`CourseUpdateApplyResult` fields.

## Keeping goals

```http
POST /admin/courses/{course}/lectures/{lecture}/practice-design/intent/keep
```

Course managers only, no body, CSRF like other mutations. It re-approves the same
goals, constraints and professor-fixed tasks for the lecture's current source
revision as an explicit new professor approval: a new `LearningIntentApproval`
with the acting professor and time; the previous design and its approval record
are archived unchanged in the design history. Goal IDs and order are preserved.
The goals' source anchors must still occur in the current sources (deterministic
check after parsing outside the course lock); otherwise the professor reviews or
regenerates them. Returns the practice design like `.../intent/approve`; `409`
unless the lecture has approved goals that are stale only because its sources
changed.

Teaching implementation stays AI-owned and is regenerated by the normal draft
flow. Professor-fixed tasks cannot be regenerated, so a design with fixed tasks
keeps its implementation, which must validate against the current sources; the
draft flow then reviews and repairs the AI-owned part. Only an all-fixed design
keeps its advisory review. Regenerating goals instead uses the existing proposal
endpoint, which replaces stale goals with a new proposal for review.

## Lecture states

```http
GET /admin/courses/{course}/lecture-states
```

Course managers only. Cheap: no model calls, no source parsing and no course lock;
publication validity comes from the workspace validity cache and only the newest
generation record per lecture is parsed (`courses/lecture_states.py`).

```json
{
  "course_id": "ml",
  "routing": "confirmed",
  "lectures": [
    {
      "lecture_id": "lecture-02",
      "number": "02",
      "title": "Gradient Descent",
      "date": "2026-10-08",
      "published": true,
      "published_at": "2026-10-12T20:13:32Z",
      "sources": "changed",
      "goals": "stale",
      "draft": "none",
      "draft_error": null,
      "next_action": "keep_or_regenerate_goals"
    }
  ]
}
```

| Field     | Values and meaning                                                                                                                                                                                                                                                                                                                                                                                  |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `routing` | `confirmed` when the routing is confirmed for the current index and schedule; else `needs_review`                                                                                                                                                                                                                                                                                                   |
| `sources` | `new`: never published and no approved goals; `changed`: the newer of the goal approval and the publication is bound to another revision than the current one; else `current`                                                                                                                                                                                                                       |
| `goals`   | `approved` for the current revision; `proposing` while a leased proposal job runs; `stale` when approved for an older revision; `needs_review` for an unapproved proposal of the current revision; else `missing`                                                                                                                                                                                   |
| `draft`   | `generating` while a generation record holds its lease; with approved goals: `ready` for a draft bound to the current goals and sources that differs from the publication, `published` when the publication is bound to the current goals and sources, `failed` when the newest generation after the goal approval failed or was interrupted (`draft_error` carries its stored detail); else `none` |

`next_action` is the single most useful step: `confirm_routing` while routing needs
review (unless the lecture is published and current), then `wait` (proposing),
`review_goals` (missing or needs review), `keep_or_regenerate_goals` (stale), then
by draft: `wait`, `retry_draft`, `review_draft`, `generate_draft` or `none`.
