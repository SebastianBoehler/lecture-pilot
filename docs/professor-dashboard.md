# Professor dashboards

Course performance loads the professor's managed published workspaces from the
server. It does not depend on which course was last selected in the builder.
The course selector resets lecture selection and analytics when its course changes.
Loading and request errors remain explicit; old course results are not reused.

The overview prioritizes learners, first-attempt quiz correctness and independent
first-pass outcomes. Sample sizes and insufficient-data states remain visible.
Independent, supported and delayed outcomes remain separate in lecture details.
Technical publication, map and gate revisions are available in disclosures.
An approved gate title is used only when its revision matches the current metric;
historical evidence retains its recorded identifier.

Usage shows model requests, tokens and admitted tutor requests. Tutor counters
include failed admitted requests and must not be labeled completed conversations.
Token breakdowns, recording coverage and quota settings are secondary disclosures.
The activity chart covers every calendar day in the server-returned period, with
selectable model calls, tutor requests or tokens and an accessible daily table.
A gap means no recorded activity, not proof that the service was unused.

Learning performance currently has aggregate, revision-bound outcome cells, not
comparable time-series cohorts. Do not graph these as historical learning gains.
A future learning trend needs dated cohort definitions, consistent task/publication
bindings and minimum-sample suppression in the backend. The usage chart does not
measure learning effectiveness.

Course management keeps course titles, term, lecture counts and access information.
Internal course IDs and repeated instructor identifiers are omitted from the list.

UI ownership: `ProfessorPerformanceDashboard` discovers courses;
`ProfessorCoursePerformance` loads their course/lecture analytics;
`UsageActivityChart` renders `usageHistoryData` calendar totals. No provider or
backend analytics contract changed in this redesign.

## Verification, 6 September 2026

- Production build and `verify:fast` passed; the existing large math chunk warning remains.
- Full serial web run: 401/402 passed. The unrelated expired-session route assertion
  failed once; it passed in a subsequent 20-test run covering session restoration,
  dashboard selection, outcome bindings, usage controls and chart calendar handling.
- Live browser: published-course switching, lecture details, usage periods, disclosures,
  course management and light/dark themes checked at about 1000px width with no horizontal
  overflow. No new runtime errors followed the corrected development module import.
- The local Usage response had no recorded activity. Populated chart behavior was tested
  in component tests; no synthetic records were added to the running app. A phone viewport
  was not exercised in this pass. Backend contracts were unchanged; API tests were not rerun.
