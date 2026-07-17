import type {
  Attendance,
  CanvasPublicationResult,
  CanvasDocument,
  CanvasSection,
  CanvasSectionPlacement,
  ExamReadinessAnswer,
  ExamReadinessAttemptResult,
  ExamReadinessCheck,
  ExamRevisionTask,
  Lecture,
  LearnerWorkspaceMode,
  LoginSession,
  UniversityCourse,
} from "./types";
import { authRequestInit, learnerRequestInit } from "./authz";
import { readApiError } from "./apiError";
import { resolveApiBaseUrl } from "./apiBaseUrl";
import { normalizeLectureList } from "./lectureMapping";

export { readApiError } from "./apiError";

export type CanvasCommand = {
  type: "focus_section" | "highlight_span" | "open_artifact" | "append_section" | "update_section";
  section_id?: string | null;
  span_id?: string | null;
  highlight_text?: string | null;
  artifact_id?: string | null;
  section?: CanvasSection | null;
  placement?: CanvasSectionPlacement | null;
};

export type AgentTurnResult = {
  message: string;
  session_goal?: string | null;
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
  course_id: string;
  lecture_id: string;
  attendance: Attendance;
  message: string;
  canvas_state: {
    focused_section_id: string;
  };
  readiness_task?: ExamRevisionTask | null;
};

type AgentTurnStreamEvent =
  | { type: "activity"; tag: string }
  | { type: "result"; result: AgentTurnResult }
  | { type: "error"; message: string };

const apiBaseUrl = resolveApiBaseUrl(import.meta.env.PROD, import.meta.env.VITE_API_BASE_URL);

export function apiUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function sendAgentTurn(
  input: AgentTurnInput,
  session: LoginSession,
  mode: LearnerWorkspaceMode = "learner",
): Promise<AgentTurnResult> {
  const response = await fetch(
    `${apiBaseUrl}/agent/turn`,
    learnerRequestInit(session, mode, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  );

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
  {
    onActivity,
    mode = "learner",
  }: { onActivity?: (tag: string) => void; mode?: LearnerWorkspaceMode } = {},
): Promise<AgentTurnResult> {
  const response = await fetch(
    `${apiBaseUrl}/agent/turn/stream`,
    learnerRequestInit(session, mode, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  );

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(readApiError(payload, "Tutor stream failed."));
  }
  if (!response.body) {
    return sendAgentTurn(input, session, mode);
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
  session: LoginSession,
  mode: LearnerWorkspaceMode = "learner",
): Promise<CanvasDocument> {
  const response = await fetch(
    apiUrl(`/courses/${courseId}/lectures/${lectureId}/canvas`),
    learnerRequestInit(session, mode),
  );
  const payload = await response.json();
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : "Canvas loading failed.";
    throw new Error(detail);
  }

  return payload as CanvasDocument;
}

export async function getDraftLectureCanvas(
  courseId: string,
  lectureId: string,
  session: LoginSession,
): Promise<CanvasDocument> {
  const response = await fetch(
    apiUrl(`/admin/courses/${courseId}/lectures/${lectureId}/canvas/draft`),
    authRequestInit(session),
  );
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Canvas draft loading failed."));
  return payload as CanvasDocument;
}

export async function publishLectureCanvas(
  courseId: string,
  lectureId: string,
  session: LoginSession,
): Promise<CanvasPublicationResult> {
  const response = await fetch(
    apiUrl(`/admin/courses/${courseId}/lectures/${lectureId}/canvas/publish`),
    authRequestInit(session, {
      method: "POST",
    }),
  );
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Canvas publish failed."));
  return payload as CanvasPublicationResult;
}

export async function getCanvasPublication(
  courseId: string,
  lectureId: string,
  session: LoginSession,
): Promise<CanvasPublicationResult> {
  const response = await fetch(
    apiUrl(`/courses/${courseId}/lectures/${lectureId}/canvas/publication`),
    {
      ...authRequestInit(session),
    },
  );
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Canvas publication status failed."));
  return payload as CanvasPublicationResult;
}

export async function getExamReadinessCheck(
  courseId: string,
  session: LoginSession,
): Promise<ExamReadinessCheck> {
  const response = await fetch(apiUrl(`/courses/${courseId}/exam-readiness`), {
    ...authRequestInit(session),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Exam readiness check loading failed."));
  return payload as ExamReadinessCheck;
}

export async function submitExamReadinessAttempt(
  courseId: string,
  answers: ExamReadinessAnswer[],
  session: LoginSession,
): Promise<ExamReadinessAttemptResult> {
  const response = await fetch(
    apiUrl(`/courses/${courseId}/exam-readiness/attempts`),
    authRequestInit(session, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers }),
    }),
  );
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Exam readiness submission failed."));
  return payload as ExamReadinessAttemptResult;
}

export async function getCourseLectures(
  courseId: string,
  session: LoginSession,
): Promise<Lecture[]> {
  const response = await fetch(apiUrl(`/courses/${courseId}/lectures`), {
    ...authRequestInit(session),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Course lecture loading failed."));
  return normalizeLectureList(payload);
}

export async function getCourses(session: LoginSession): Promise<UniversityCourse[]> {
  const response = await fetch(apiUrl("/courses"), {
    ...authRequestInit(session),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Course loading failed."));
  return payload as UniversityCourse[];
}
