import type { ChatMessage, LoginSession } from "./types";

export const initialMessages: ChatMessage[] = [
  {
    id: "agent-welcome",
    role: "agent",
    content:
      "I’m starting from the lecture canvas. Mark whether you attended, then I’ll either verify the key ideas or guide you through the material.",
    toolTags: ["gate: needs evidence"],
  },
];

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
