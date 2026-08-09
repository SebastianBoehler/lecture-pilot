export type LearnerGateStatus = "passed" | "needs_evidence";

export type LearnerQuizState = {
  selected_index: number;
  correct: boolean | null;
  publication_version: number;
  attempt_index: number;
  first_attempt_correct: boolean | null;
  latest_outcome: "correct" | "incorrect" | "unscored";
  correction_state: "not_needed" | "needed" | "corrected";
};

export type LearnerLessonState = {
  course_id: string;
  lecture_id: string;
  publication_version: number;
  gate_statuses: Record<string, LearnerGateStatus>;
  quiz_states: Record<string, LearnerQuizState>;
  active_session_goal: string | null;
  pending_check: {
    gate_id: string;
    gate_revision: string;
    prompt: string;
    assistance_level: "none" | "prompt" | "hint" | "worked_step" | "worked_example";
    kind: "standard" | "delayed_transfer";
  } | null;
  due_gate_reviews: Array<{
    gate_id: string;
    gate_revision: string;
    due_at: string;
  }>;
};
