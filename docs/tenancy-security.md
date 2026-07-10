# Tenancy and authorization matrix

LecturePilot derives tenant, user, role, and course authority from the current database session.
Browser-supplied user IDs are never authority. Production disables OpenAPI and development-header
authentication.

## Principals

| Principal              | Authority                                                                         |
| ---------------------- | --------------------------------------------------------------------------------- |
| Public                 | Health check, student university login, and professor signup/login                 |
| Pending professor      | Own account and approval state; no learner or course-authoring capability          |
| Enrolled student       | Own unlocked lectures, canvas, assets, tutor turns, quiz events, readiness, reset |
| Approved professor     | May create a course; gains no tenant-wide content access                          |
| Course owner           | Manages only the course whose `owner_user_id` matches the session user            |
| Platform administrator | Approves/disables accounts; gains no course or learner-content access             |

Tutor and co-instructor delegation is not implemented. Platform course search and join requests are
also deferred.

Student identities come only from the university adapter. Professor identities use a separate
LecturePilot email/password account. Passwords are stored only as Argon2id hashes. Registration
creates a pending request atomically and grants no role; platform-admin approval revokes existing
sessions, and the professor must sign in again before course-authoring tools become available.
Production web builds do not render either development demo login.

## Route inventory

| Class                       | Routes                                                                                                | Required object check                                                      |
| --------------------------- | ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Public                      | `GET /health`, `POST /auth/login`, `POST /auth/professor/register`, `POST /auth/professor/login`       | Rate-limited; submitted credentials are never logged or returned           |
| Self-service                | `GET /me`, `POST /auth/logout`, `POST /professor-requests`                                            | Current opaque session; professor requests require a professor account     |
| Platform administration     | `/platform/professor-requests*`, `POST /platform/users/{id}/disable`                                  | `platform_admin`; no course-content capability                             |
| Course discovery            | `GET /courses`, `GET /courses/{course}/lectures`                                                      | Database visibility or enrollment; lecture unlock server-side              |
| Learner-only                | `POST /agent/turn*`, canvas, learning map, quiz answer, readiness, learner reset, workspace assets    | Current session user plus active course enrollment; no learner ID accepted |
| Course-owner administration | Course creation, source bundle, schedule, upload, draft, publish, media, aggregate analytics, archive | Approved professor for creation; exact `courses.owner_user_id` thereafter  |
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

1. Discard upstream memberships without a stable Alma `unitId` or ILIAS course/ref ID.
2. Reuse an existing `(tenant, source, external_course_id, term)` binding when present.
3. Otherwise compare normalized exact title and exact term with active platform courses.
4. Bind and enroll only when exactly one course matches. Zero or multiple matches grant nothing.
5. After binding, the stable upstream ID remains authoritative even if the displayed title changes.

## Denial rules

- An unrelated professor, tutor, or platform administrator cannot read or mutate another course.
- No professor or administrator can access a learner canvas, chat, memory, files, readiness history,
  reset, or agent turn.
- Public and pre-attempt DTOs omit storage paths, staff identity, readiness answers, and rubrics.
- Every cookie-authenticated mutation requires the session CSRF token, an allowed Origin, and valid
  Fetch Metadata.
