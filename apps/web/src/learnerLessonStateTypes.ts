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
    assistance_level: "none" | "prompt" | "cue" | "faded_example" | "worked_step";
    kind: "standard" | "delayed_transfer";
    task_id?: string;
    issued_at?: string;
    stage?:
      | "diagnostic"
      | "diagnostic_support"
      | "independent_exit"
      | "exit_support"
      | "delayed_transfer"
      | "delayed_support";
    assistance_content?: string | null;
    focus_required?: boolean;
    bank_exhausted?: boolean;
  } | null;
  goal_evidence?: Array<{
    gate_id: string;
    gate_revision: string;
    supported: boolean;
    independent: boolean;
    delayed: boolean;
    missing_evidence_ids: string[];
    missing_evidence?: string[];
  }>;
  due_gate_reviews: Array<{
    gate_id: string;
    gate_revision: string;
    due_at: string;
  }>;
};
