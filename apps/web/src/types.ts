export type Theme = "light" | "dark";
export type View = "login" | "dashboard" | "lesson" | "profile";
export type LessonPanelMode = "chat" | "outline" | "notes" | "files";
export type CanvasSectionId = string;
export type DocumentAnchorId = string;

export type Attendance = "unknown" | "present" | "absent";

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
  type: "paragraph" | "list" | "asset" | "callout" | "math";
  text?: string | null;
  items: string[];
  asset_path?: string | null;
  asset_url?: string | null;
  caption?: string | null;
};

export type CanvasSection = {
  id: string;
  title: string;
  source_ref?: string | null;
  blocks: CanvasBlock[];
};

export type CanvasDocument = {
  id: string;
  import_version?: number;
  course_id: string;
  lecture_id: string;
  title: string;
  source_kind: "latex" | "markdown" | "generated";
  source_ref: string;
  workspace_path: string;
  sections: CanvasSection[];
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

export type WorkspaceResource = {
  id: string;
  kind: "canvas" | "source" | "asset";
  label: string;
  path: string;
  detail?: string | null;
  url?: string | null;
};
