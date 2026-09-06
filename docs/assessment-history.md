# Private assessment history

Readiness results already persist in each learner's course `progress.json`. The
tutor now receives a bounded, current-lecture excerpt of those recorded outcomes
and submitted practice-exam answers. The backend loads this after resolving the
learner workspace identity; the browser cannot supply this history. Professor
preview uses its separate preview identity.

Practice exam drafts remain in tab storage until **Finish and review**. This
explicit action saves an immutable private submission before opening the existing
solution sheet. Storage is `users/<user-key>/courses/<course-id>/practice-exams/
<exam-id>/attempts/<uuid>.json`. The immutable exam supplies the question snapshot;
each submission also records its source revision and server timestamp. Retrying
the same submission ID and answers returns the saved record. Reusing the ID for
different answers fails. Inputs stay frozen while a submission is being retried.

The exam dialog's **Saved attempts** section loads previous submissions for review
and offers deletion. Deleting an exam removes its submissions; course/account
workspace deletion removes the enclosing private files. A deleted attempt is
absent from subsequent tutor-history reads. Previously delivered chat content or
an already-running tutor turn is not retroactively erased.

There is no new grading service. Practice submissions retain answers with
`assessment: ungraded` and `assistance: unknown`. The existing solution sheet
compares multiple-choice answers locally and shows reference answers for open
questions. Those self-check scores are not persisted grades. Readiness records
retain their existing automatic-choice or AI-assessment provenance; historical
readiness records do not contain the student's original answer.

`assessment_history.py` reads the authoritative private records for the resolved
user/course and includes only the current lecture. Practice questions requiring
other lectures are excluded from that lecture's tutor context. At most 12 recent
question observations are included; long practice prompts/answers are explicitly
marked as excerpts. Historical feedback is untrusted data and advisory context,
not current course truth or independent mastery. It cannot pass a gate. Answer
keys, rubrics, and reference solutions are not added to this context. Course staff
have no submission-history endpoint; existing professor aggregates are unchanged.

The endpoints are student/enrollment protected GET and POST
`/courses/{course_id}/practice-exams/{exam_id}/attempts` and DELETE on
`.../attempts/{attempt_id}`. They accept no user ID, reject unknown/inactive question
IDs and invalid answer kinds, and share a lock with exam deletion.
