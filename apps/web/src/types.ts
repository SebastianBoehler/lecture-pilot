import type { LearningMap } from "./learningMapTypes";
import type { UniversityEnrollmentCourse } from "./universityCourseTypes";

export type Theme = "light" | "dark";
export type InfoPageKind = "how-it-works" | "learning-science" | "privacy";
export type View =
  | "login"
  | "dashboard"
  | "lesson"
  | "profile"
  | "professor"
  | "performance"
  | "course-management"
  | InfoPageKind;
export type LessonPanelMode = "chat" | "outline" | "path" | "notes" | "files";
export type CanvasSectionId = string;
export type DocumentAnchorId = string;

export type Attendance = "unknown" | "present" | "absent";
export type TenantRole = "tenant_admin" | "professor" | "tutor" | "student";
export type CourseAccessPolicy = "public" | "platform_authenticated" | "tuebingen_enrolled";

export type Lecture = {
  id: string;
  number: string;
  title: string;
  date: string;
  attendance: Attendance;
  materialPath?: string;
};

export type CanvasBlock = {
  id: string;
  type:
    | "paragraph"
    | "list"
    | "asset"
    | "callout"
    | "math"
    | "video"
    | "checkpoint"
    | "quiz"
    | "table"
    | "component";
  text?: string | null;
  items: string[];
  asset_path?: string | null;
  asset_url?: string | null;
  caption?: string | null;
  answer_index?: number | null;
  component_id?: string | null;
  component_type?: string | null;
  component_ref?: string | null;
  component_version?: number | null;
  option_ids?: string[];
};

export type CanvasSection = {
  id: string;
  title: string;
  source_ref?: string | null;
  blocks: CanvasBlock[];
};

export type CanvasSectionPlacement = {
  mode: "after_section" | "before_section";
  section_id: string;
};

export type CanvasDocument = {
  id: string;
  import_version?: number;
  course_id: string;
  lecture_id: string;
  title: string;
  source_kind: "latex" | "markdown" | "generated";
  source_ref: string;
  workspace_path?: string;
  sections: CanvasSection[];
  warnings?: string[];
};

export type CanvasPublicationResult = {
  course_id: string;
  lecture_id: string;
  published: boolean;
  version?: number | null;
  published_at?: string | null;
};

export type ExamReadinessQuestion = {
  id: string;
  kind: "multiple_choice" | "open_ended";
  lecture_id: string;
  lecture_title: string;
  section_id: string;
  section_title: string;
  prompt: string;
  options: string[];
  source_ref?: string | null;
};

export type ExamReadinessCoverage = {
  lecture_id: string;
  lecture_title: string;
  question_count: number;
};

export type ExamReadinessCheck = {
  course_id: string;
  passing_score: number;
  published_lecture_count: number;
  coverage: ExamReadinessCoverage[];
  questions: ExamReadinessQuestion[];
};

export type ExamReadinessAnswer = {
  question_id: string;
  selected_index?: number | null;
  text?: string | null;
};

export type ExamReadinessQuestionResult = {
  question_id: string;
  kind: "multiple_choice" | "open_ended";
  lecture_id: string;
  section_id: string;
  answer_kind: "multiple_choice" | "open_ended";
  correct: boolean | null;
  selected_index?: number | null;
  correct_index?: number | null;
  status: "correct" | "incorrect" | "needs_rubric_review";
};

export type ExamReadinessGuidanceLevel = "challenge" | "standard" | "scaffolded";

export type TutorScaffoldPolicy = {
  trigger: "readiness_task" | "conceptual" | "procedural" | "error";
  learner_stage: "novice" | "early_intermediate" | "late_intermediate";
  profile: "worked_example" | "faded_example" | "self_explanation" | "transfer";
  process_label:
    "shallow_lookup" | "scaffolded_reasoning" | "self_explanation" | "transfer_attempt";
  tutor_move: string;
  forbidden: string;
};

export type ExamRevisionTask = {
  id: string;
  question_id: string;
  kind: "review_wrong_mc" | "review_open_answer";
  status: "open" | "completed";
  guidance_level: ExamReadinessGuidanceLevel;
  lecture_id: string;
  lecture_title: string;
  section_id: string;
  section_title: string;
  prompt: string;
  source_ref?: string | null;
  rubric: string[];
  expected_evidence: string;
  next_action: string;
  scaffold_policy: TutorScaffoldPolicy;
};

export type ExamReadinessAttemptResult = {
  attempt_id?: string | null;
  created_at?: string | null;
  course_id: string;
  passing_score: number;
  score: number | null;
  guidance_level: ExamReadinessGuidanceLevel;
  results: ExamReadinessQuestionResult[];
  tasks: ExamRevisionTask[];
};

export type SourceBundleEntry = {
  path: string;
  kind: string;
  size_bytes: number;
};

export type SourceBundleManifest = {
  course_id: string;
  files: SourceBundleEntry[];
  counts_by_kind: Record<string, number>;
};

export type LectureScheduleItem = {
  number: string;
  title: string;
  date: string;
  material_path?: string | null;
};

export type LectureScheduleProposal = {
  course_id: string;
  lectures: LectureScheduleItem[];
  source_paths: string[];
};

export type CourseWorkspaceResult = {
  course: UniversityCourse;
  lectures: Lecture[];
  active_lecture_id: string;
};

export type YoutubeVideoCandidate = {
  video_id: string;
  title: string;
  channel_title: string;
  description: string;
  url: string;
  thumbnail_url?: string | null;
  duration: { display?: string | null; seconds?: number | null };
  score: number;
  reason: string;
};

export type UniversityCourse = {
  access_policy?: CourseAccessPolicy;
  id: string;
  title: string;
  professor: string;
  term: string;
};

export type LoginSession = {
  username: string;
  display_name?: string | null;
  email?: string | null;
  term: string;
  tenant_id?: string;
  account_type?: "student" | "professor";
  university_role?: string | null;
  roles?: TenantRole[];
  access_token?: string | null;
  auth_transport?: "bearer" | "cookie" | "dev_headers";
  csrf_token?: string | null;
  courses: UniversityCourse[];
  university_courses?: UniversityEnrollmentCourse[];
};

export type LearningGoal = "keep_up" | "understand_deeply" | "exam_preparation";

export type LearnerFile = {
  path: string;
  size_bytes: number;
  content?: string | null;
};

export type LearnerCourseProfile = {
  course_id: string;
  memory: string;
  passed_lecture_ids: string[];
  files: LearnerFile[];
};

export type LearnerProfile = {
  onboarding_completed: boolean;
  learning_goal?: LearningGoal | null;
  preferences: Record<string, unknown>;
  global_notes: string;
  global_files: LearnerFile[];
  courses: LearnerCourseProfile[];
};

export type ChatMessage = {
  id: string;
  role: "agent" | "user";
  content: string;
  isPending?: boolean;
  toolTags?: string[];
};

export type WorkspaceResource = {
  id: string;
  kind: "canvas" | "source" | "asset" | "video" | "memory";
  label: string;
  path: string;
  sectionId?: string | null;
  blockId?: string | null;
  displayPath?: string | null;
  detail?: string | null;
  url?: string | null;
};

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
};

export type LectureAnalyticsSummary = {
  course_id: string;
  lecture_id: string;
  total_events: number;
  learning_map?: LearningMap | null;
  quizzes: AnalyticsQuizMetric[];
  gates: AnalyticsGateMetric[];
};
