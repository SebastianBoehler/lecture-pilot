# Production testing usage — observed 6 September 2026

Read-only inspection of `lecturepilot.cs.uni-tuebingen.de`, at approximately
13:18–13:21 UTC. Running API image:
`lecturepilot-api:2324744a72c072726201903f8cf04623df7d8938`.
These figures describe that deployed version and retained production records,
not the current local authoring/learning-flow implementation or local benchmarks.

## Presentation headline

**Early production testing: 40 university-authenticated accounts, 20 tutor-active
accounts, and 309 recorded tutor requests.**

The 40 accounts include one identified course-owner/admin/operator account.
Excluding that account leaves 39 accounts; all 20 tutor-active accounts and all
309 quota-recorded requests remain. This exclusion is based on course ownership,
platform-admin membership and the known operator's external identity. It does
not establish that every remaining account was an independent student tester.

| Measure                                            | Observed result | Definition                                                      |
| -------------------------------------------------- | --------------: | --------------------------------------------------------------- |
| Retained accounts                                  |              40 | Distinct database accounts, all with Tübingen identity provider |
| Accounts excluding identified owner/admin/operator |              39 | Cohort exclusion above                                          |
| Tutor-active accounts                              |              20 | Accounts with positive daily turn counters                      |
| Recorded tutor requests                            |             309 | Admitted requests counted by quota reservation                  |
| Mean requests per tutor-active account             |           15.45 | 309 / 20; not divided by all registered accounts                |
| Median requests per tutor-active account           |             9.5 | Median of each active account's cumulative count                |
| Largest individual request count                   |              74 | Explains why mean exceeds median                                |
| Tutor-active on multiple dates                     |          5 / 20 | At least two distinct recorded usage dates                      |
| Login events                                       |             145 | Successful login audit events across all 40 accounts            |
| Accounts logging in on multiple dates              |              11 | Includes operator; distinct UTC audit dates                     |
| Tutor provider records                             |             668 | Model-call records, not student turns                           |
| Tutor tokens                                       |       3,754,535 | Recorded provider total tokens                                  |
| All-workload provider records                      |           1,002 | Tutor plus course canvas/schedule generation                    |
| All-workload tokens                                |       5,738,392 | Recorded usage, not a reconciled invoice                        |

Do not label accounts as unique people, requests as completed conversations,
multiple-date activity as long-term retention, or testing as proven learning.
No explicit `capacity-synthetic-`, `demo-` or `test-` identity prefix matched.
This is a narrow marker check, not proof that developer-led testing is absent.

## Timing and concentration

Retained account creation spans 11 July–5 August 2026. Login audit events span
11 July–14 August. Tutor request counters cover these dates only:

| Usage date | Recorded tutor requests | Active accounts |
| ---------- | ----------------------: | --------------: |
| 23 July    |                     230 |              16 |
| 24 July    |                      77 |               8 |
| 5 August   |                       2 |               1 |

Daily account counts overlap; they must not be summed as unique accounts.
307 of 309 requests occurred on 23–24 July. Present this as a short testing
burst, not sustained adoption or a growing daily-active-user trend.
No later tutor usage appears in the retained counter/provider records as of
this inspection; that is not evidence that nobody subsequently read course pages.

## What the telemetry can and cannot establish

The deployed `UsageQuota.reserve_turn` increments `agent_turns` on admission.
`release_turn` decrements only active concurrency; it does not remove failed
requests from the cumulative turn count. Consequently, 309 is not a verified
count of successfully completed tutor turns.

All 668 tutor provider records have distinct request IDs, but none has an
operation ID. Provider successes cannot be reliably grouped into completed
student turns for this historical dataset. There are 332 canvas-generation
records across two retained courses, 2 schedule records, and 668 tutor records
for one course. All records are marked succeeded; historical recording coverage
must be considered before claiming that no provider failures ever occurred.

The currently retained API metadata files begin with an August 1 rotated file;
the main July testing burst is not present in these files. Two successful
`lecturepilot.agent_turn` completion spans appear in the August 5 file. Thus
the available logs confirm those two completions, not the completion rate of
all 309 requests. Log JSON records themselves lack timestamps in this retained
format; rotation names provide file-level dating only.

Account/course deletion can remove related retained records. These aggregates
are counts of surviving records, not an independently verified lifetime history.
The login window, quota window and model-usage window are different and should
not be merged into a fabricated common observation period.

## Reproduction and handling

Verified deployed table columns before issuing SQL. Queries ran inside read-only
transactions with a 15-second statement timeout; the primary aggregate used
repeatable-read isolation. Follow-up cohort and coverage checks were separate
read-only snapshots a few minutes later.

Prepared SQL and primary query output remain locally under the ignored directory
`output/production-usage-2026-09-06/`. Only aggregate data was returned from the
database and metadata scan. No learner messages, email addresses, session tokens
or raw identity values were exported. No services, settings or production data
were changed. The user-established SSH session was left available.

Suggested slide: three headline numbers (40 accounts, 20 tutor-active, 309
requests), with “median 9.5 requests per active account” beneath. Footnote:
“Retained production records; tutor activity 23 July–5 August 2026; requests
count admissions, not confirmed completions; includes testing.”
