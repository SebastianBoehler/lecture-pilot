import type {
  Attendance,
  CanvasPublicationResult,
  CanvasDocument,
  CanvasSection,
  LoginSession,
} from "./types";
import { authHeaders, courseManagerHeaders } from "./authz";

export type CanvasCommand = {
  type: "focus_section" | "highlight_span" | "open_artifact" | "append_section" | "update_section";
  section_id?: string | null;
  span_id?: string | null;
  highlight_text?: string | null;
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

export type AgentTurnInput = {
  user_id: string;
  course_id: string;
  lecture_id: string;
  attendance: Attendance;
  message: string;
  canvas_state: {
    focused_section_id: string;
  };
};

type AgentTurnStreamEvent =
  | { type: "activity"; tag: string }
  | { type: "result"; result: AgentTurnResult }
  | { type: "error"; message: string };

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

export async function sendAgentTurn(input: AgentTurnInput, session: LoginSession): Promise<AgentTurnResult> {
  const response = await fetch(`${apiBaseUrl}/agent/turn`, {
    method: "POST",
    headers: { ...authHeaders(session), "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  const payload = await response.json();
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : "Tutor turn failed.";
    throw new Error(detail);
  }

  return payload as AgentTurnResult;
}

export async function sendAgentTurnStream(
  input: AgentTurnInput,
  session: LoginSession,
  { onActivity }: { onActivity?: (tag: string) => void } = {},
): Promise<AgentTurnResult> {
  const response = await fetch(`${apiBaseUrl}/agent/turn/stream`, {
    method: "POST",
    headers: { ...authHeaders(session), "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(readApiError(payload, "Tutor stream failed."));
  }
  if (!response.body) {
    return sendAgentTurn(input, session);
  }

  return readAgentTurnStream(response.body, onActivity);
}

async function readAgentTurnStream(
  body: ReadableStream<Uint8Array>,
  onActivity?: (tag: string) => void,
): Promise<AgentTurnResult> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: AgentTurnResult | null = null;

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      finalResult = readAgentTurnStreamLine(line, onActivity) ?? finalResult;
    }
    if (done) {
      break;
    }
  }

  finalResult = readAgentTurnStreamLine(buffer, onActivity) ?? finalResult;
  if (!finalResult) {
    throw new Error("Tutor stream ended without a result.");
  }
  return finalResult;
}

function readAgentTurnStreamLine(line: string, onActivity?: (tag: string) => void) {
  if (!line.trim()) {
    return null;
  }
  const event = JSON.parse(line) as AgentTurnStreamEvent;
  if (event.type === "activity") {
    onActivity?.(event.tag);
    return null;
  }
  if (event.type === "error") {
    throw new Error(event.message);
  }
  return event.result;
}

export async function getLectureCanvas(
  courseId: string,
  lectureId: string,
  userId: string,
  session: LoginSession,
): Promise<CanvasDocument> {
  const searchParams = new URLSearchParams({ user_id: userId });
  const response = await fetch(
    apiUrl(`/courses/${courseId}/lectures/${lectureId}/canvas?${searchParams}`),
    { headers: authHeaders(session) },
  );
  const payload = await response.json();
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : "Canvas loading failed.";
    throw new Error(detail);
  }

  return payload as CanvasDocument;
}

export async function draftLectureCanvas(
  courseId: string,
  lectureId: string,
  session: LoginSession,
): Promise<CanvasDocument> {
  const response = await fetch(apiUrl(`/admin/courses/${courseId}/lectures/${lectureId}/canvas/draft`), {
    method: "POST",
    headers: courseManagerHeaders(session),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Canvas planner failed."));
  return payload as CanvasDocument;
}

export async function getDraftLectureCanvas(
  courseId: string,
  lectureId: string,
  session: LoginSession,
): Promise<CanvasDocument> {
  const response = await fetch(apiUrl(`/admin/courses/${courseId}/lectures/${lectureId}/canvas/draft`), {
    headers: courseManagerHeaders(session),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Canvas draft loading failed."));
  return payload as CanvasDocument;
}

export async function publishLectureCanvas(
  courseId: string,
  lectureId: string,
  session: LoginSession,
): Promise<CanvasPublicationResult> {
  const response = await fetch(apiUrl(`/admin/courses/${courseId}/lectures/${lectureId}/canvas/publish`), {
    method: "POST",
    headers: courseManagerHeaders(session),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Canvas publish failed."));
  return payload as CanvasPublicationResult;
}

export async function getCanvasPublication(
  courseId: string,
  lectureId: string,
  session: LoginSession,
): Promise<CanvasPublicationResult> {
  const response = await fetch(apiUrl(`/courses/${courseId}/lectures/${lectureId}/canvas/publication`), {
    headers: authHeaders(session),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Canvas publication status failed."));
  return payload as CanvasPublicationResult;
}

export function readApiError(payload: unknown, fallback: string) {
  return typeof (payload as { detail?: unknown }).detail === "string"
    ? String((payload as { detail: string }).detail)
    : fallback;
}
