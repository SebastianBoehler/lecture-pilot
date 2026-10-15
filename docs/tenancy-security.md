# Tenancy and authorization matrix

LecturePilot derives tenant, user, role, and course authority from the current database session.
Browser-supplied user IDs are never authority. Production disables OpenAPI and development-header
authentication.

## Principals

| Principal              | Authority                                                                           |
| ---------------------- | ----------------------------------------------------------------------------------- |
| Public                 | Health/readiness checks and verified email accounts                                 |
| Enrolled student       | Own unlocked lectures, canvas, assets, tutor turns, quiz events, readiness, reset   |
| Verified professor     | May create a course; gains no tenant-wide content access                            |
| Course owner           | Manages only the course whose `owner_user_id` matches the session user              |
| Platform administrator | May disable accounts and view aggregate course demand; no course or learner content |

Tutor and co-instructor delegation is not implemented. Platform course search and join requests are
also deferred.

New accounts require university email verification and begin as students. Professor and
administrator roles require an operator grant; a recovered legacy identity retains its role.
No account receives an Alma or ILIAS session. See [account setup](local-accounts.md).
Production web builds do not render either development demo login.

## Route inventory

| Class                       | Routes                                                                                                               | Required object check                                                                    |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Public                      | `GET /health`, `POST /auth/login`, register/verify/password-reset routes                                             | Rate-limited; submitted credentials are never logged or returned                         |
| Self-service                | `GET /me`, learning-profile routes, `POST /auth/logout`, `GET\|PUT\|DELETE /me/course-support-requests`              | Current opaque session; course requests need a student and an own Alma/ILIAS observation |
| Platform administration     | `POST /platform/users/{id}/disable`, `GET /platform/course-support-demand`                                           | `platform_admin`; no course-content capability; demand is counts only                    |
| Course discovery            | `GET /courses`, `GET /courses/{course}/lectures`                                                                     | Database visibility or enrollment; lecture unlock server-side                            |
| Learner-only                | `POST /agent/turn*`, canvas, learning map, quiz answer, readiness, practice exams, learner reset, workspace assets   | Current session user plus active course enrollment; no learner ID accepted               |
| Course-owner administration | Course creation, source bundle, schedule, staged updates, draft/repair/publish, media, preview, aggregates, deletion | Operator-granted or retained professor role; exact `courses.owner_user_id` thereafter    |
| Published course assets     | `GET /course-assets/{course}/{lecture}/{path}`                                                                       | Course access, publication/unlock policy, confined path                                  |

The learner-only class includes:

- `GET /courses/{course}/lectures/{lecture}/canvas`
- `GET /courses/{course}/lectures/{lecture}/learning-map`
- `GET /workspace-assets/{course}/{lecture}/{student_key}/{path}`; the URL key must resolve to the
  current learner and cannot select another learner
- `POST /courses/{course}/learner-workspace/reset`
- `POST /courses/{course}/lectures/{lecture}/analytics/quiz-answer`
- `GET /courses/{course}/exam-readiness`
- `POST /courses/{course}/exam-readiness/attempts`
- `POST /courses/{course}/practice-exam-generations`
- `GET /courses/{course}/practice-exam-generations/status`
- `GET|DELETE /courses/{course}/practice-exams/{exam}`
- `GET /courses/{course}/practice-exams/{exam}/pdf`

Course support requests reference only the session user's stored Alma/ILIAS observation
(`source`, `external_course_id`, `term`; anything else is 404). Platform demand and the professor
builder hint (`GET /admin/course-support-demand/match`, any professor) return tenant-scoped counts
only: no names, usernames or user IDs. Requests live in the Postgres table
`course_support_requests` (one row per user, source, course ID and term; `ON DELETE CASCADE` from
`users`); audit events record only the request ID and source, never course titles.

The course-owner class includes every `/admin/courses/{course}/*` route plus course deletion. Staged
course updates compare server-computed hashes, never interpret missing upload paths as deletions,
and do not mutate published canvases. The class returns aggregate analytics only and never accepts
or returns learner identifiers.

Learning-design reports and their acknowledgements are private course-builder state. Approval binds
the exact report revision and diagnostic ID set to the current draft, source, and learning-map
revisions; publication revalidates that binding and never copies the report to learner content.

## Existing enrollments and sessions

Historical Alma/ILIAS records remain as saved access evidence. Login no longer fetches
university memberships or changes saved enrollments. New students use lecturer-issued
join links. Public Alma search remains available without university authentication.

Email verification reclaims exactly one existing account with a matching university
email, preserving its ID, role and private workspace. Ambiguous matches fail explicitly.
Disabled accounts remain inaccessible. New accounts receive no historical memberships.

Opaque cookie sessions renew after half their idle lifetime has elapsed. Their absolute
lifetime still requires a fresh LecturePilot login, one day by default. Expired, revoked
and disabled-account sessions remain rejected. Password reset revokes all user sessions;
the authentication migration revokes every session created before the change.

## Denial rules

- An unrelated professor, tutor, or platform administrator cannot read or mutate another course.
- Professor usage summaries aggregate only provider metadata and counters for courses owned by
  the active professor; they never expose learner text or another professor's course activity.
- No professor or administrator can access a learner canvas, chat, memory, files, readiness history,
  reset, or agent turn.
- Outcome events exclude learner answer text, tutor messages, conditions, randomization, and browser
  timing. Professor preview produces no learner outcome event, and aggregates remain hidden below
  five unique learners.
- Public and pre-attempt DTOs omit storage paths, staff identity, readiness answers, and rubrics.
- Practice-exam DTOs and PDFs omit answer keys, rubrics, and course-source IDs.
- Model prompts are not logged or persisted in database events.
- Cookie-authenticated mutations outside the public authentication routes require the session CSRF token, an allowed Origin, and valid
  Fetch Metadata.
