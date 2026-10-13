/** Contract of `GET /admin/courses/{course_id}/lecture-states`. */
export type LectureNextAction =
  | "none"
  | "confirm_routing"
  | "review_goals"
  | "keep_or_regenerate_goals"
  | "wait"
  | "generate_draft"
  | "retry_draft"
  | "review_draft";

export type LectureState = {
  lecture_id: string;
  number: string;
  title: string;
  date: string;
  published: boolean;
  published_at: string | null;
  sources: "current" | "changed" | "new";
  goals: "approved" | "stale" | "needs_review" | "proposing" | "missing";
  draft: "none" | "generating" | "ready" | "failed" | "published";
  draft_error: string | null;
  next_action: LectureNextAction;
};

export type CourseLectureStates = {
  course_id: string;
  routing: "confirmed" | "needs_review";
  lectures: LectureState[];
};
