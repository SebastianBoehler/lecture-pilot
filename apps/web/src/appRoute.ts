import type { LessonMode, View } from "./types";

export type AppRoute =
  | {
      view: "lesson";
      courseId: string;
      lectureId: string;
      lessonMode: LessonMode;
    }
  | {
      view: "course-management";
      updateCourseId?: string;
    }
  | {
      view: Exclude<View, "lesson" | "course-management">;
    };

const VIEW_PATHS: Record<Exclude<View, "lesson">, string> = {
  login: "/",
  dashboard: "/workspaces",
  profile: "/profile",
  professor: "/professor/courses/new",
  performance: "/professor/performance",
  usage: "/professor/usage",
  "course-management": "/professor/courses",
  changelog: "/changelog",
  "how-it-works": "/how-it-works",
  "learning-science": "/learning-science",
  privacy: "/privacy",
};

export function readAppRoute(location: Pick<Location, "pathname" | "search">): AppRoute {
  const legacyDraft = legacyDraftRoute(location.search);
  if (legacyDraft) return legacyDraft;

  const segments = location.pathname.split("/").filter(Boolean).map(decodeSegment);
  if (
    segments[0] === "professor" &&
    segments[1] === "courses" &&
    segments[3] === "lectures" &&
    (segments[5] === "preview" || segments[5] === "draft")
  ) {
    return {
      view: "lesson",
      courseId: segments[2],
      lectureId: segments[4],
      lessonMode: segments[5] === "draft" ? "draft" : "professor-preview",
    };
  }
  if (segments[0] === "courses" && segments[2] === "lectures" && segments.length === 4) {
    return {
      view: "lesson",
      courseId: segments[1],
      lectureId: segments[3],
      lessonMode: "learner",
    };
  }
  if (segments[0] === "professor" && segments[1] === "courses" && segments[3] === "update") {
    return { view: "course-management", updateCourseId: segments[2] };
  }

  const path = normalizePath(location.pathname);
  if (path === VIEW_PATHS["course-management"]) return { view: "course-management" };
  const match = Object.entries(VIEW_PATHS).find(([, routePath]) => routePath === path);
  return {
    view: (match?.[0] as Exclude<View, "lesson" | "course-management"> | undefined) ?? "login",
  };
}

export function pathForView(view: Exclude<View, "lesson">) {
  return VIEW_PATHS[view];
}

export function lessonPath(courseId: string, lectureId: string, mode: LessonMode = "learner") {
  const course = encodeURIComponent(courseId);
  const lecture = encodeURIComponent(lectureId);
  if (mode === "learner") return `/courses/${course}/lectures/${lecture}`;
  return `/professor/courses/${course}/lectures/${lecture}/${
    mode === "draft" ? "draft" : "preview"
  }`;
}

export function courseUpdatePath(courseId: string) {
  return `/professor/courses/${encodeURIComponent(courseId)}/update`;
}

export function requiresSession(view: View) {
  return !["login", "changelog", "how-it-works", "learning-science", "privacy"].includes(view);
}

function legacyDraftRoute(search: string): AppRoute | null {
  const params = new URLSearchParams(search);
  if (params.get("preview") !== "draft") return null;
  return {
    view: "lesson",
    courseId: params.get("courseId") ?? "martius-ml",
    lectureId: params.get("lectureId") ?? "lecture-03",
    lessonMode: "draft",
  };
}

function normalizePath(pathname: string) {
  return pathname === "/" ? pathname : pathname.replace(/\/+$/, "");
}

function decodeSegment(segment: string) {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment;
  }
}
