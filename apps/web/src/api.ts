import type {
  Attendance,
  CanvasDocument,
  CanvasSection,
  LoginSession,
  SourceBundleManifest,
  YoutubeVideoCandidate,
} from "./types";

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
const professorHeaders = {
  "X-Tenant-Id": "tenant-tuebingen",
  "X-User-Id": "professor-demo",
  "X-User-Role": "professor",
};

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

export async function draftLectureCanvas(courseId: string, lectureId: string): Promise<CanvasDocument> {
  const response = await fetch(apiUrl(`/admin/courses/${courseId}/lectures/${lectureId}/canvas/draft`), {
    method: "POST",
    headers: professorHeaders,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Canvas planner failed."));
  return payload as CanvasDocument;
}

export async function getSourceBundle(courseId = "martius-ml"): Promise<SourceBundleManifest> {
  const response = await fetch(apiUrl(`/courses/${courseId}/source-bundle`));
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Source scan failed."));
  return payload as SourceBundleManifest;
}

export async function uploadCourseMaterial(input: {
  courseId: string;
  path: string;
  file: File;
}) {
  const body = new FormData();
  body.append("path", input.path);
  body.append("file", input.file);
  const response = await fetch(apiUrl(`/admin/courses/${input.courseId}/materials`), {
    method: "POST",
    headers: professorHeaders,
    body,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Material upload failed."));
  return payload as { path: string; kind: string; size_bytes: number };
}

export async function searchYoutubeMedia(courseId: string, query: string) {
  const params = new URLSearchParams({ q: query, max_results: "5" });
  const response = await fetch(apiUrl(`/admin/courses/${courseId}/media/youtube/search?${params}`), {
    headers: professorHeaders,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "YouTube search failed."));
  return payload as { items: YoutubeVideoCandidate[] };
}

export async function includeYoutubeMedia(input: {
  courseId: string;
  lectureId: string;
  sectionId: string | null;
  video: YoutubeVideoCandidate;
}) {
  const response = await fetch(
    apiUrl(`/admin/courses/${input.courseId}/lectures/${input.lectureId}/media/youtube`),
    {
      method: "POST",
      headers: { ...professorHeaders, "Content-Type": "application/json" },
      body: JSON.stringify({ section_id: input.sectionId, video: input.video }),
    },
  );
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "YouTube include failed."));
  return payload as { block_id: string };
}

export async function clearCourseYoutubeMedia(courseId: string) {
  const response = await fetch(apiUrl(`/admin/courses/${courseId}/media/youtube`), {
    method: "DELETE",
    headers: professorHeaders,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Course media reset failed."));
  return payload as { deleted: number };
}

function readApiError(payload: unknown, fallback: string) {
  return typeof (payload as { detail?: unknown }).detail === "string"
    ? String((payload as { detail: string }).detail)
    : fallback;
}
