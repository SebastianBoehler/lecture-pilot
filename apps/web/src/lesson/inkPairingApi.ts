import { apiRequest } from "../shared/apiRequest";
import type { LoginSession } from "../shared/types";

export type InkLecture = { courseId: string; lectureId: string; session: LoginSession };

export function inkPairRequest<T>(
  lecture: InkLecture,
  method: "POST" | "GET" | "PUT" | "DELETE",
  failure: string,
  { code, image, signal }: { code?: string; image?: string; signal?: AbortSignal } = {},
) {
  const path = `/courses/${encodeURIComponent(lecture.courseId)}/lectures/${encodeURIComponent(lecture.lectureId)}/ink-pair`;
  return apiRequest<T>(
    lecture.session,
    code ? `${path}/${encodeURIComponent(code)}` : path,
    failure,
    {
      method,
      signal,
      cache: "no-store",
      headers: image ? { "Content-Type": "application/json" } : undefined,
      body: image ? JSON.stringify({ image }) : undefined,
    },
  );
}

export function inkPairCode(hash: string) {
  const code = new URLSearchParams(hash.slice(1)).get("ink");
  return code && /^[A-Za-z0-9_-]{32}$/.test(code) ? code : null;
}
