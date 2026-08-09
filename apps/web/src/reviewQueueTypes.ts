export type GateReviewQueueItem = {
  id: string;
  kind: "gate_review" | "gate_repair";
  course_id: string;
  lecture_id: string;
  lecture_title: string;
  section_id: string;
  section_title: string;
  gate_id: string;
  gate_revision: string;
  due_at: string;
};

export type ReadinessReviewQueueItem = {
  id: string;
  kind: "readiness_repair";
  course_id: string;
  lecture_id: string;
  lecture_title: string;
  section_id: string;
  section_title: string;
  task_id: string;
  next_action: string;
};

export type ReviewQueueItem = GateReviewQueueItem | ReadinessReviewQueueItem;

export type CourseReviewQueue = {
  course_id: string;
  items: ReviewQueueItem[];
};

export type GateReviewOpening = {
  course_id: string;
  lecture_id: string;
  section_id: string;
  gate_id: string;
  gate_revision: string;
  prompt: string;
  stage: "due" | "repair";
};
