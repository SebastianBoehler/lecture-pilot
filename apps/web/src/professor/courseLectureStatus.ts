import type { LectureNextAction, LectureState } from "./courseLectureStateTypes";

export type LectureStatusKind =
  | "generating"
  | "proposing"
  | "failed"
  | "draft_ready"
  | "routing"
  | "goals_review"
  | "sources_changed"
  | "draft_needed"
  | "published"
  | "not_published";

export type LectureStatusTone = "progress" | "attention" | "danger" | "success" | "neutral";

/** One status per lecture: running work first, then what the professor must decide. */
export function lectureStatus(lecture: LectureState): {
  kind: LectureStatusKind;
  tone: LectureStatusTone;
} {
  if (lecture.draft === "generating") return { kind: "generating", tone: "progress" };
  if (lecture.goals === "proposing") return { kind: "proposing", tone: "progress" };
  if (lecture.draft === "failed") return { kind: "failed", tone: "danger" };
  if (lecture.draft === "ready") return { kind: "draft_ready", tone: "attention" };
  if (lecture.next_action === "confirm_routing") return { kind: "routing", tone: "attention" };
  if (lecture.goals === "needs_review" || lecture.goals === "missing") {
    return { kind: "goals_review", tone: "attention" };
  }
  if (lecture.goals === "stale" || lecture.sources === "changed") {
    return { kind: "sources_changed", tone: "attention" };
  }
  if (lecture.next_action === "generate_draft") return { kind: "draft_needed", tone: "attention" };
  if (lecture.published) return { kind: "published", tone: "success" };
  return { kind: "not_published", tone: "neutral" };
}

export function isLectureBusy(lecture: LectureState) {
  return (
    lecture.goals === "proposing" ||
    lecture.draft === "generating" ||
    lecture.next_action === "wait"
  );
}

const ATTENTION: readonly LectureNextAction[] = [
  "confirm_routing",
  "review_goals",
  "keep_or_regenerate_goals",
  "generate_draft",
  "retry_draft",
  "review_draft",
];

export function needsProfessor(lecture: LectureState) {
  return ATTENTION.includes(lecture.next_action);
}

export function courseLectureSummary(lectures: readonly LectureState[]) {
  return {
    total: lectures.length,
    published: lectures.filter((lecture) => lecture.published).length,
    needsReview: lectures.filter(needsProfessor).length,
    readyToPublish: lectures.filter((lecture) => lecture.next_action === "review_draft").length,
  };
}
