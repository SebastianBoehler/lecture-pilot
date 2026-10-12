import type { CourseReviewQueue, GateReviewQueueItem, ReviewQueueItem } from "./reviewQueueTypes";
import type { Lecture } from "./types";

export type LectureReason = "missed" | "diagnostic" | "continue" | "review";

export type NextUpAction =
  | { kind: "queue"; item: ReviewQueueItem; lecture: Lecture }
  | { kind: "lecture"; lecture: Lecture; reason: LectureReason };

export type NextUpReview = {
  item: ReviewQueueItem;
  lecture: Lecture;
  due: boolean;
};

/** The single best next step: due/repair queue work first, then the next lecture to learn. */
export function bestNextAction(
  lectures: Lecture[],
  passedLectureIds: string[],
  queue: CourseReviewQueue | null,
): NextUpAction | null {
  for (const item of queue?.items ?? []) {
    const lecture = lectures.find((candidate) => candidate.id === item.lecture_id);
    if (lecture) return { kind: "queue", item, lecture };
  }
  if (!lectures.length) return null;
  const passed = new Set(passedLectureIds);
  const incomplete = lectures.filter((lecture) => !passed.has(lecture.id));
  const missed = incomplete.find((lecture) => lecture.attendance === "absent");
  if (missed) return { kind: "lecture", lecture: missed, reason: "missed" };
  const diagnostic = incomplete.find((lecture) => lecture.attendance === "unknown");
  if (diagnostic) return { kind: "lecture", lecture: diagnostic, reason: "diagnostic" };
  if (incomplete[0]) return { kind: "lecture", lecture: incomplete[0], reason: "continue" };
  return { kind: "lecture", lecture: lectures.at(-1)!, reason: "review" };
}

/** Remaining due work and this week's planned gate reviews, excluding the primary action. */
export function remainingReviews(
  lectures: Lecture[],
  queue: CourseReviewQueue | null,
  primary: NextUpAction | null,
): NextUpReview[] {
  if (!queue) return [];
  const primaryId = primary?.kind === "queue" ? primary.item.id : null;
  const entries: NextUpReview[] = [];
  const add = (item: ReviewQueueItem, due: boolean) => {
    const lecture = lectures.find((candidate) => candidate.id === item.lecture_id);
    if (lecture && item.id !== primaryId) entries.push({ item, lecture, due });
  };
  queue.items.forEach((item) => add(item, true));
  queue.upcoming.forEach((item) => add(item, false));
  return entries;
}

export function calendarReviews(queue: CourseReviewQueue | null): GateReviewQueueItem[] {
  if (!queue) return [];
  return [
    ...queue.items.filter((item): item is GateReviewQueueItem => item.kind === "gate_review"),
    ...queue.upcoming,
  ];
}
