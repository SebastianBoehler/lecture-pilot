export type PracticeExamQuestion = {
  id: string;
  kind: "multiple_choice" | "open_ended";
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
  ppi_source_ids: string[];
};

export type PracticeExamAnswer = { selected_index?: number; text?: string };
export type PracticeExamAnswers = Record<string, PracticeExamAnswer>;

export type PpiExamFile = {
  path: string;
  text_path: string;
  media_type: string;
  sha256: string;
  size_bytes: number;
  character_count: number;
};

export type PpiExamSource = {
  id: string;
  ppi_lecture_id: number;
  title: string;
  protocol_count: number;
  imported_at: string;
  borrowed_until?: string | null;
  source_filename: string;
  archive_sha256: string;
  files: PpiExamFile[];
};

export type PpiCatalogLecture = {
  id: number;
  title: string;
  protocol_count: number;
  borrowed: boolean;
  can_borrow: boolean;
  download_available: boolean;
  borrowed_until?: string | null;
  cached_source_id?: string | null;
};

export type PpiCatalog = {
  tokens: number;
  lectures: PpiCatalogLecture[];
  cached_sources: PpiExamSource[];
};

export type PpiCredentials = { username: string; password: string };

export type PracticeExamGenerationStatus = {
  generation_id: string;
  status: "running" | "completed" | "failed";
  attempt: number;
  error_code?: string | null;
  exam_id?: string | null;
};
