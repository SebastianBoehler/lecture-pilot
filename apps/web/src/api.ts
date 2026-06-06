import type { Attendance, CanvasDocument, CanvasSection, LoginSession } from "./types";

export type CanvasCommand = {
  type: "focus_section" | "highlight_span" | "open_artifact" | "append_section" | "update_section";
  section_id?: string | null;
  span_id?: string | null;
  artifact_id?: string | null;
  section?: CanvasSection | null;
};

export type AgentTurnResult = {
  message: string;
  canvas_commands: CanvasCommand[];
  quality_gate?: {
    gate_id: string;
    status: "passed" | "needs_evidence" | "not_assessed";
    reason: string;
    next_prompt?: string | null;
  } | null;
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

type TuebingenLoginInput = {
  username: string;
  password: string;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export function apiUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function loginWithTuebingen(input: TuebingenLoginInput): Promise<LoginSession> {
  const response = await fetch(`${apiBaseUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  const payload = await response.json();
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : "Login failed.";
    throw new Error(detail);
  }

  return payload as LoginSession;
}

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

export async function getLectureCanvas(
  courseId: string,
  lectureId: string,
  userId: string,
): Promise<CanvasDocument> {
  const searchParams = new URLSearchParams({ user_id: userId });
  const response = await fetch(
    apiUrl(`/courses/${courseId}/lectures/${lectureId}/canvas?${searchParams}`),
  );
  const payload = await response.json();
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : "Canvas loading failed.";
    throw new Error(detail);
  }

  return payload as CanvasDocument;
}
