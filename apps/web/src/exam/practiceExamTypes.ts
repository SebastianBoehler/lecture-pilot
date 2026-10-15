type PracticeExamQuestion = {
  id: string;
  kind: "multiple_choice" | "multiple_select" | "open_ended";
  status?: "active" | "invalid";
  prompt: string;
  points: number;
  options: string[];
};

export type PracticeExam = {
  id: string;
  course_id: string;
  title: string;
  language: string;
  instructions: string[];
  duration_minutes: number;
  created_at: string;
  total_points: number;
  questions: PracticeExamQuestion[];
};

export type PracticeExamGenerationInput = {
  question_count: number;
  duration_minutes: number;
  choice_format?: "single_answer" | "multiple_answers";
};

export type PracticeExamAnswer = {
  selected_index?: number;
  selected_indices?: number[];
  text?: string;
};
export type PracticeExamAnswers = Record<string, PracticeExamAnswer>;

export type PracticeExamSolutionQuestion = {
  id: string;
  kind: "multiple_choice" | "multiple_select" | "open_ended";
  status?: "active" | "invalid";
  points: number;
  answer_index: number | null;
  answer_indices?: number[];
  reference_answer: string | null;
  rubric: string[];
};

export type PracticeExamSolutionSheet = {
  exam_id: string;
  title: string;
  total_points: number;
  questions: PracticeExamSolutionQuestion[];
};

export type PracticeExamGenerationStatus = {
  generation_id: string;
  status: "running" | "completed" | "failed";
  attempt: number;
  error_code?: string | null;
  exam_id?: string | null;
};
