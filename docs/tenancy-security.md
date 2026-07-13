# Tenancy and authorization matrix

LecturePilot derives tenant, user, role, and course authority from the current database session.
Browser-supplied user IDs are never authority. Production disables OpenAPI and development-header
authentication.

## Principals

| Principal              | Authority                                                                         |
| ---------------------- | --------------------------------------------------------------------------------- |
| Public                 | Health check and university login                                                   |
| Enrolled student       | Own unlocked lectures, canvas, assets, tutor turns, quiz events, readiness, reset |
| Alma professor         | May create a course; gains no tenant-wide content access                          |
| Course owner           | Manages only the course whose `owner_user_id` matches the session user            |
| Platform administrator | May disable accounts; gains no course or learner-content access                   |

Tutor and co-instructor delegation is not implemented. Platform course search and join requests are
also deferred.

University identities come only from the server-side adapter. The active Alma `student` role maps to
a student account; any other active Alma role maps directly to a professor account. LecturePilot
stores the active and available server-reported roles for audit, but never accepts a role from the
browser.
Production web builds do not render either development demo login.

## Route inventory

| Class                       | Routes                                                                                                | Required object check                                                      |
| --------------------------- | ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Public                      | `GET /health`, `POST /auth/login`                                                   | Rate-limited; submitted credentials are never logged or returned           |
| Self-service                | `GET /me`, `POST /auth/logout`                                                                      | Current opaque session                                                      |
| Platform administration     | `POST /platform/users/{id}/disable`                                                                 | `platform_admin`; no course-content capability                              |
| Course discovery            | `GET /courses`, `GET /courses/{course}/lectures`                                                      | Database visibility or enrollment; lecture unlock server-side              |
| Learner-only                | `POST /agent/turn*`, canvas, learning map, quiz answer, readiness, learner reset, workspace assets    | Current session user plus active course enrollment; no learner ID accepted |
| Course-owner administration | Course creation, source bundle, schedule, upload, draft, publish, media, aggregate analytics, archive | Verified non-student Alma role; exact `courses.owner_user_id` thereafter   |
| Published course assets     | `GET /course-assets/{course}/{lecture}/{path}`                                                        | Course access, publication/unlock policy, confined path                    |

The learner-only class includes:

- `GET /courses/{course}/lectures/{lecture}/canvas`
- `GET /courses/{course}/lectures/{lecture}/learning-map`
- `GET /workspace-assets/{course}/{lecture}/{student_key}/{path}`; the URL key must resolve to the
  current learner and cannot select another learner
- `POST /courses/{course}/learner-workspace/reset`
- `POST /courses/{course}/lectures/{lecture}/analytics/quiz-answer`
- `GET /courses/{course}/exam-readiness`
- `POST /courses/{course}/exam-readiness/attempts`

The course-owner class includes every `/admin/courses/{course}/*` route plus course deletion. It
returns aggregate analytics only and never accepts or returns learner identifiers.

## University matching

LecturePilot cannot enumerate an Alma or ILIAS catalog. A professor creates a platform course using
title and term. On student login, only that student's own upstream memberships are considered.

1. Treat Alma timetable titles as term-scoped evidence with a deterministic title key; require a
   stable course/ref ID for ILIAS memberships.
2. Reuse an existing `(tenant, source, external_course_id, term)` binding when present.
3. Otherwise compare normalized exact title and exact term with active platform courses.
4. Bind and enroll only when exactly one course matches. Zero or multiple matches grant nothing.
5. ILIAS bindings remain authoritative across title changes. Alma remains exact-name-and-term based
   because its lightweight timetable does not expose an immutable course ID.

Authentication verifies the active Alma role before issuing a session. Previous Alma/ILIAS-derived
enrollments are deactivated at that boundary; Alma timetable and ILIAS data then synchronize in
parallel, and only the current sync attempt may restore matched course access. The dashboard polls
`GET /me` while this work is in progress and does not treat browser course data as authority.

## Denial rules

- An unrelated professor, tutor, or platform administrator cannot read or mutate another course.
- Professor usage summaries aggregate only provider metadata and counters for courses owned by
  the active professor; they never expose learner text or another professor's course activity.
- No professor or administrator can access a learner canvas, chat, memory, files, readiness history,
  reset, or agent turn.
- Public and pre-attempt DTOs omit storage paths, staff identity, readiness answers, and rubrics.
- Every cookie-authenticated mutation requires the session CSRF token, an allowed Origin, and valid
  Fetch Metadata.
