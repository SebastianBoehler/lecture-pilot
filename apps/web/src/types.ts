export type Theme = "light" | "dark";
export type View = "login" | "dashboard" | "lesson" | "profile";
export type LessonPanelMode = "chat" | "outline" | "notes";
export type CanvasSectionId =
  | "learning-goals"
  | "feature-maps"
  | "kernel-trick"
  | "skill-check"
  | "failure-mode";
export type ArtifactBlockId =
  | "artifact-counter"
  | "artifact-summary"
  | "artifact-quiz"
  | "artifact-code"
  | "artifact-diagram"
  | "artifact-playground"
  | "artifact-video";
export type DocumentAnchorId = CanvasSectionId | ArtifactBlockId;

export type Attendance = "unknown" | "present" | "absent";

export type Lecture = {
  id: string;
  number: string;
  title: string;
  date: string;
  attendance: Attendance;
  materialPath?: string;
};

export type UniversityCourse = {
  id: string;
  title: string;
  professor: string;
  term: string;
};

export type LoginSession = {
  username: string;
  email?: string | null;
  term: string;
  courses: UniversityCourse[];
};

export type ChatMessage = {
  id: string;
  role: "agent" | "user";
  content: string;
  toolTags?: string[];
};
