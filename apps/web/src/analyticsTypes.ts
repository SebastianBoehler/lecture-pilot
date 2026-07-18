import type { LearningMap } from "./learningMapTypes";

export type AnalyticsOptionMetric = {
  option_index: number;
  option_id?: string | null;
  text: string;
  selections: number;
  correct: boolean;
};

export type AnalyticsQuizMetric = {
  component_id: string;
  component_type: string;
  title: string;
  question: string;
  total_attempts: number;
  unique_learners: number;
  correct_attempts: number;
  correct_rate: number | null;
  latest_activity?: string | null;
  attendance_split: Record<string, number>;
  options: AnalyticsOptionMetric[];
};

export type AnalyticsGateMetric = {
  gate_id: string;
  total_events: number;
  unique_learners: number;
  latest_activity?: string | null;
  status_counts: Record<string, number>;
  attendance_split: Record<string, number>;
  independent_attempts: number;
  independent_passes: number;
  supported_attempts: number;
  transfer_attempts: number;
  independent_transfer_passes: number;
  assistance_level_counts: Record<string, number>;
  evidence_counts: Record<string, number>;
};

export type LectureAnalyticsSummary = {
  course_id: string;
  lecture_id: string;
  total_events: number;
  learning_map?: LearningMap | null;
  quizzes: AnalyticsQuizMetric[];
  gates: AnalyticsGateMetric[];
};
