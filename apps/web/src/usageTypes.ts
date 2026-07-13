export type UsageTotals = {
  model_requests: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cached_input_tokens: number;
  reasoning_tokens: number;
  tutor_turns: number;
  images: number;
};

export type UsageActivity = {
  model_requests: number;
  total_tokens: number;
  tutor_turns: number;
  images: number;
};

export type ProfessorUsageSummary = {
  period_start: string;
  period_end: string;
  totals: UsageTotals;
  workloads: Array<Pick<UsageActivity, "model_requests" | "total_tokens"> & { workload: string }>;
  courses: Array<UsageActivity & { course_id: string; course_title: string }>;
  daily: Array<UsageActivity & { date: string }>;
  limits: {
    turns_per_day: number;
    reserved_tokens_per_day: number;
    images_per_day: number;
    concurrent_turns: number;
    tokens_per_turn: number;
  };
};
