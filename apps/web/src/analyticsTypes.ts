import type { LearningMap } from "./learningMapTypes";

export type AnalyticsOutcomeCell = {
  evidence_type: string;
  sample_size: number;
  data_status: "available" | "insufficient_data";
  rate: number | null;
};

export type AnalyticsVersionStatus = "current" | "historical";

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
  publication_version: number;
  version_status: AnalyticsVersionStatus;
  activity_events: number;
  unique_learners: number;
  first_attempt: AnalyticsOutcomeCell;
  correction_after_feedback: AnalyticsOutcomeCell;
  options: AnalyticsOptionMetric[] | null;
};

export type AnalyticsGateMetric = {
  gate_id: string;
  gate_revision: string;
  publication_version: number;
  version_status: AnalyticsVersionStatus;
  activity_events: number;
  unique_learners: number;
  independent_first_pass: AnalyticsOutcomeCell;
  supported_retry: AnalyticsOutcomeCell;
  delayed_transfer: AnalyticsOutcomeCell;
};

export type LectureAnalyticsSummary = {
  course_id: string;
  lecture_id: string;
  activity_events: number;
  unique_learners: number;
  current_publication_version: number;
  current_learning_map_revision: string;
  learning_map?: LearningMap | null;
  quizzes: AnalyticsQuizMetric[];
  gates: AnalyticsGateMetric[];
};

export type CourseLectureAnalytics = {
  lecture_id: string;
  activity_events: number;
  unique_learners: number;
  current_publication_version: number;
  quiz_first_attempt: AnalyticsOutcomeCell;
  correction_after_feedback: AnalyticsOutcomeCell;
  independent_first_pass: AnalyticsOutcomeCell;
  supported_retry: AnalyticsOutcomeCell;
  delayed_transfer: AnalyticsOutcomeCell;
};

export type CourseAnalyticsSummary = {
  course_id: string;
  activity_events: number;
  unique_learners: number;
  quiz_first_attempt: AnalyticsOutcomeCell;
  correction_after_feedback: AnalyticsOutcomeCell;
  independent_first_pass: AnalyticsOutcomeCell;
  supported_retry: AnalyticsOutcomeCell;
  delayed_transfer: AnalyticsOutcomeCell;
  lectures: CourseLectureAnalytics[];
};
