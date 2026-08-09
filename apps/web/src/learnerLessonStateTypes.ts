export type LearnerGateStatus = "passed" | "needs_evidence" | "not_assessed";

export type LearnerQuizState = {
  selected_index: number;
  correct: boolean | null;
};

export type LearnerLessonState = {
  course_id: string;
  lecture_id: string;
  gate_statuses: Record<string, LearnerGateStatus>;
  quiz_states: Record<string, LearnerQuizState>;
  active_session_goal: string | null;
  pending_check: {
    gate_id: string;
    gate_revision: string | null;
    prompt: string;
    assistance_level: "none" | "prompt" | "hint" | "worked_step" | "worked_example";
    kind: "standard" | "delayed_transfer";
  } | null;
  due_gate_reviews: Array<{
    gate_id: string;
    gate_revision: string | null;
    due_at: string;
  }>;
};
