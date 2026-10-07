import type { Locale } from "./i18nContext";
import { messages } from "./i18nMessages";
import type { GateReviewOpening } from "./reviewQueueTypes";
import type { Attendance, ChatMessage, LessonPanelMode, LoginSession } from "./types";

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
