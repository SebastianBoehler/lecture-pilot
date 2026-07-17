import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import type { CanvasDocument, LoginSession } from "./types";

export class CanvasDraftRequestError extends Error {
  readonly terminalGeneration: boolean;

  constructor(message: string, terminalGeneration: boolean) {
    super(message);
    this.name = "CanvasDraftRequestError";
    this.terminalGeneration = terminalGeneration;
  }
}

export async function draftLectureCanvas(
  courseId: string,
  lectureId: string,
  session: LoginSession,
): Promise<CanvasDocument> {
  const storageKey = canvasGenerationStorageKey(courseId, lectureId);
  const requestKey = window.sessionStorage.getItem(storageKey) ?? globalThis.crypto.randomUUID();
  window.sessionStorage.setItem(storageKey, requestKey);
  const response = await fetch(
    apiUrl(`/admin/courses/${courseId}/lectures/${lectureId}/canvas/draft`),
    authRequestInit(session, {
      method: "POST",
      headers: { "Idempotency-Key": requestKey },
    }),
  );
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const terminalGeneration = response.headers.get("X-Generation-Status") === "failed";
    if (terminalGeneration && window.sessionStorage.getItem(storageKey) === requestKey) {
      window.sessionStorage.removeItem(storageKey);
    }
    throw new CanvasDraftRequestError(
      readApiError(payload, "Canvas generation request failed."),
      terminalGeneration,
    );
  }
  if (window.sessionStorage.getItem(storageKey) === requestKey) {
    window.sessionStorage.removeItem(storageKey);
  }
  return payload as CanvasDocument;
}

function canvasGenerationStorageKey(courseId: string, lectureId: string) {
  return `lecturepilot:canvas-generation:${courseId}:${lectureId}`;
}
