import type { Attendance } from "./types";

type CanvasCommand = {
  type: "focus_section" | "highlight_span" | "open_artifact";
  section_id?: string | null;
  span_id?: string | null;
  artifact_id?: string | null;
};

export type AgentTurnResult = {
  message: string;
  canvas_commands: CanvasCommand[];
  model: string;
};

type AgentTurnInput = {
  user_id: string;
  course_id: string;
  lecture_id: string;
  attendance: Attendance;
  message: string;
  canvas_state: {
    focused_section_id: string;
  };
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function sendAgentTurn(input: AgentTurnInput): Promise<AgentTurnResult> {
  const response = await fetch(`${apiBaseUrl}/agent/turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  const payload = await response.json();
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : "Tutor turn failed.";
    throw new Error(detail);
  }

  return payload as AgentTurnResult;
}
