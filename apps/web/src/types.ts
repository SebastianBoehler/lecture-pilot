export type Theme = "light" | "dark";
export type View = "login" | "dashboard" | "lesson" | "profile" | "professor";
export type LessonPanelMode = "chat" | "outline" | "notes" | "files";
export type CanvasSectionId = string;
export type DocumentAnchorId = string;

export type Attendance = "unknown" | "present" | "absent";
export type TenantRole = "tenant_admin" | "professor" | "tutor" | "student";

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
  id: string;
  title: string;
  professor: string;
  term: string;
};

export type LoginSession = {
  username: string;
  email?: string | null;
  term: string;
  tenant_id?: string;
  roles?: TenantRole[];
  courses: UniversityCourse[];
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
  kind: "canvas" | "source" | "asset" | "video";
  label: string;
  path: string;
  displayPath?: string | null;
  detail?: string | null;
  url?: string | null;
};
