export type Theme = "light" | "dark";
export type View = "dashboard" | "lesson";

export type Attendance = "unknown" | "present" | "absent";

export type Lecture = {
  id: string;
  number: string;
  title: string;
  date: string;
  attendance: Attendance;
};

export type CanvasSectionId =
  | "learning-goals"
  | "feature-maps"
  | "kernel-trick"
  | "skill-check"
  | "failure-mode";

export type ChatMessage = {
  id: string;
  role: "agent" | "user";
  content: string;
  toolTags?: string[];
};
