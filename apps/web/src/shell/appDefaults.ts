import type { AppRoute } from "./appRoute";
import type { Locale } from "../i18n/i18nContext";
import { messages } from "../i18n/i18nMessages";
import type { GateReviewOpening } from "../dashboard/reviewQueueTypes";
import type {
  Attendance,
  ChatMessage,
  Lecture,
  LessonPanelMode,
  LoginSession,
} from "../shared/types";

export function initialMessagesForAttendance(
  attendance: Attendance,
  review?: GateReviewOpening,
  locale: Locale = "en",
): ChatMessage[] {
  if (review) {
    return [
      {
        id: `agent-review-${review.gate_id}`,
        role: "agent",
        content: review.prompt,
      },
    ];
  }
  return [
    {
      id: "agent-welcome",
      role: "agent",
      content: messages[locale][`tutor.welcome.${attendance}`],
    },
  ];
}

/** Phones open on the lecture itself; wider screens show the tutor beside it. */
export function defaultLessonPanel(): LessonPanelMode | null {
  const compact =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(max-width: 860px)").matches;
  return compact ? null : "chat";
}

export const localDemoSession: LoginSession = {
  username: "local-demo",
  display_name: "Demo Student",
  email: null,
  term: "Sommer 2026",
  tenant_id: "tenant-tuebingen",
  account_type: "student",
  roles: ["student"],
  auth_transport: "dev_headers",
  courses: [
    {
      access_policy: "public",
      id: "martius-ml",
      title: "Grundlagen des Maschinellen Lernens",
      professor: "Prof. Georg Martius",
      term: "Sommer 2026",
    },
  ],
};

export const localProfessorSession: LoginSession = {
  ...localDemoSession,
  username: "professor-demo",
  email: "professor-demo@uni-tuebingen.de",
  account_type: "professor",
  roles: ["professor"],
};

/** Lesson routes name their course; development builds prefer the local demo course. */
export function initialCourseId(route: AppRoute) {
  if (route.view === "lesson") return route.courseId;
  return import.meta.env.DEV ? localDemoSession.courses[0].id : "";
}

/** A lesson route starts from its lecture id until the backend lecture list arrives. */
export function initialLecture(route: AppRoute): Lecture | null {
  if (route.view !== "lesson") return null;
  return {
    id: route.lectureId,
    number: route.lectureId.replace(/^lecture-/, ""),
    title: "Lecture",
    date: "",
    attendance: "unknown",
  };
}
