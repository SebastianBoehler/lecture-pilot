import type { Attendance, ChatMessage, LoginSession } from "./types";

export function initialMessagesForAttendance(attendance: Attendance): ChatMessage[] {
  return [{
    id: "agent-welcome",
    role: "agent",
    content: initialMessage(attendance),
    toolTags: [`mode: ${modeLabel(attendance)}`],
  }];
}

function initialMessage(attendance: Attendance) {
  if (attendance === "present") {
    return "You marked this lecture as attended. I’ll start in verification mode and check the key ideas before reteaching.";
  }
  if (attendance === "absent") {
    return "You marked this lecture as missed. I’ll start in guided walkthrough mode and teach from the lecture canvas.";
  }
  return "Attendance is unknown for this lecture. I’ll start in diagnostic mode and locate the first missing concept.";
}

function modeLabel(attendance: Attendance) {
  if (attendance === "present") return "verification";
  if (attendance === "absent") return "guided walkthrough";
  return "diagnostic";
}

export const localDemoSession: LoginSession = {
  username: "local-demo",
  email: null,
  term: "Sommer 2026",
  courses: [
    {
      id: "martius-ml",
      title: "Grundlagen des Maschinellen Lernens",
      professor: "Prof. Georg Martius",
      term: "Sommer 2026",
    },
  ],
};
