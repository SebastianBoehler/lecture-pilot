import type { LessonMode, View } from "../shared/types";

export type AppRoute =
  | {
      view: "lesson";
      courseId: string;
      lectureId: string;
      lessonMode: LessonMode;
    }
  | {
      view: "course-management";
      /** A single managed course page; absent for the course list. */
      courseId?: string;
    }
  | {
      /** Shared course link (QR code); `code` is present only for explicit join links. */
      view: "course-link";
      courseId: string;
      code?: string;
    }
  | {
      view: Exclude<View, "lesson" | "course-management" | "course-link">;
    };

const VIEW_PATHS: Record<Exclude<View, "lesson" | "course-link">, string> = {
  login: "/",
  dashboard: "/workspaces",
  profile: "/profile",
  professor: "/professor/courses/new",
  performance: "/professor/performance",
  usage: "/professor/usage",
  "course-demand": "/platform/course-demand",
  "course-management": "/professor/courses",
  changelog: "/changelog",
  "how-it-works": "/how-it-works",
  "learning-science": "/learning-science",
  privacy: "/privacy",
};

export function readAppRoute(location: Pick<Location, "pathname">): AppRoute {
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
  if (segments[0] === "courses" && segments.length === 2) {
    return { view: "course-link", courseId: segments[1] };
  }
  if (segments[0] === "join" && segments.length === 3) {
    return { view: "course-link", courseId: segments[1], code: segments[2] };
  }
  if (
    segments[0] === "professor" &&
    segments[1] === "courses" &&
    segments.length === 3 &&
    segments[2] !== "new"
  ) {
    return { view: "course-management", courseId: segments[2] };
  }

  const path = normalizePath(location.pathname);
  if (path === VIEW_PATHS["course-management"]) return { view: "course-management" };
  const match = Object.entries(VIEW_PATHS).find(([, routePath]) => routePath === path);
  return {
    view:
      (match?.[0] as Exclude<View, "lesson" | "course-management" | "course-link"> | undefined) ??
      "login",
  };
}

export function pathForView(view: Exclude<View, "lesson" | "course-link">) {
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

export function lessonKey(courseId: string, lectureId: string, mode: LessonMode) {
  return `${mode}:${courseId}:${lectureId}`;
}

export function coursePagePath(courseId: string) {
  return `/professor/courses/${encodeURIComponent(courseId)}`;
}

export function requiresSession(view: View) {
  return ![
    "login",
    "changelog",
    "how-it-works",
    "learning-science",
    "privacy",
    "course-link",
  ].includes(view);
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
