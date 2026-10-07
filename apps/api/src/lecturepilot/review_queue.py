from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from lecturepilot.coaching_episode import matching_pending
from lecturepilot.coaching_progress import CoachingProgressStore, InvalidCoachingStateError
from lecturepilot.learning_map import LearningMap
from lecturepilot.readiness_progress import ReadinessProgressStore
from lecturepilot.review_queue_models import (
    CompletedGateReview,
    CourseReviewQueue,
    GateReviewQueueItem,
    ReadinessReviewQueueItem,
)
from lecturepilot.storage_layout import StorageLayout
from lecturepilot.review_queue_order import interleave_lectures


@dataclass(frozen=True)
class ReviewQueueLecture:
    id: str
    title: str
    learning_map: LearningMap


class ReviewQueueStore:
    def __init__(self, layout: StorageLayout) -> None:
        self.coaching = CoachingProgressStore(layout)
        self.readiness = ReadinessProgressStore(layout)

    def read_course(
        self,
        *,
        user_id: str,
        course_id: str,
        lectures: list[ReviewQueueLecture],
        now: datetime | None = None,
    ) -> CourseReviewQueue:
        current_time = now or datetime.now(UTC)
        due: list[tuple[datetime, GateReviewQueueItem]] = []
        upcoming: list[tuple[datetime, GateReviewQueueItem]] = []
        repairs: list[GateReviewQueueItem] = []
        completed: list[tuple[datetime, CompletedGateReview]] = []
        maps_by_lecture = {lecture.id: lecture.learning_map for lecture in lectures}
        lecture_titles = {lecture.id: lecture.title for lecture in lectures}
        for lecture in lectures:
            progress = self.coaching.read(
                user_id=user_id,
                course_id=course_id,
                lecture_id=lecture.id,
            )
            gates = {gate.id: gate for gate in lecture.learning_map.gates}
            sections = {node.section_id: node.title for node in lecture.learning_map.nodes}
            for review in progress.delayed_reviews.values():
                gate = gates.get(review.gate_id)
                if gate is None or review.gate_revision != gate.revision:
                    raise InvalidCoachingStateError(
                        "Persisted delayed review does not match the published learning map."
                    )
                if review.section_id not in sections or review.section_id != gate.section_id:
                    raise InvalidCoachingStateError("Persisted delayed review section is invalid.")
                completion = review.last_completed_at or review.completed_at
                if completion is not None:
                    if completion >= current_time - timedelta(days=7):
                        completed.append(
                            (
                                completion,
                                CompletedGateReview(
                                    id=f"completed:{lecture.id}:{gate.id}",
                                    course_id=course_id,
                                    lecture_id=lecture.id,
                                    section_title=sections[review.section_id],
                                    completed_at=completion.isoformat(),
                                ),
                            )
                        )
                if review.completed_at is not None:
                    continue
                due_at = review.due_at
                item = GateReviewQueueItem(
                    id=(
                        f"gate:{lecture.id}:{gate.id}"
                        if review.attempted_at is None
                        else f"gate-repair:{lecture.id}:{gate.id}"
                    ),
                    kind="gate_review" if review.attempted_at is None else "gate_repair",
                    course_id=course_id,
                    lecture_id=lecture.id,
                    lecture_title=lecture.title,
                    section_id=review.section_id,
                    section_title=sections[review.section_id],
                    gate_id=gate.id,
                    gate_revision=gate.revision,
                    due_at=review.due_at.isoformat(),
                )
                if review.attempted_at is None and due_at <= current_time:
                    due.append((due_at, item))
                elif review.attempted_at is None and due_at <= current_time + timedelta(days=7):
                    upcoming.append((due_at, item))
                elif review.attempted_at is not None and _has_active_repair(
                    progress.pending_check, gate.id, gate.revision
                ):
                    repairs.append(item)
        readiness = self.readiness.read(user_id=user_id, course_id=course_id)
        readiness_items = [
            ReadinessReviewQueueItem(
                id=f"readiness:{task.id}",
                course_id=course_id,
                lecture_id=task.lecture_id,
                lecture_title=lecture_titles[task.lecture_id],
                section_id=task.section_id,
                section_title=task.section_title,
                task_id=task.id,
                next_action=task.next_action,
            )
            for task in readiness.active_tasks
            if task.status == "open"
            and task.lecture_id in maps_by_lecture
            and any(
                node.section_id == task.section_id
                for node in maps_by_lecture[task.lecture_id].nodes
            )
        ]
        ordered_due = [
            item
            for _, item in sorted(
                due,
                key=lambda pair: (pair[0], pair[1].lecture_id, pair[1].gate_id),
            )
        ]
        repairs.sort(key=lambda item: (item.lecture_id, item.gate_id))
        readiness_items.sort(key=lambda item: (item.lecture_id, item.task_id))
        return CourseReviewQueue(
            course_id=course_id,
            items=[
                *interleave_lectures(ordered_due),
                *interleave_lectures(repairs),
                *interleave_lectures(readiness_items),
            ],
            upcoming=interleave_lectures(
                [
                    item
                    for _, item in sorted(
                        upcoming,
                        key=lambda pair: (pair[0], pair[1].lecture_id, pair[1].gate_id),
                    )
                ]
            ),
            completed=[
                item for _, item in sorted(completed, key=lambda pair: pair[0], reverse=True)
            ],
        )


def _has_active_repair(pending, gate_id: str, gate_revision: str) -> bool:
    active = matching_pending(pending, gate_id, gate_revision)
    return active is not None and active.kind == "standard"
