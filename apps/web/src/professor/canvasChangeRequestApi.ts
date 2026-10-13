import { apiRequest } from "../shared/apiRequest";
import type { LoginSession } from "../shared/types";

/** Contract of `GET /admin/courses/{course}/lectures/{lecture}/canvas/change-request`. */
export type CanvasChangeOptions = {
  base: "draft" | "published";
  sections: { id: string; title: string }[];
  latest: {
    instruction: string;
    section_ids: string[];
    selection: "professor" | "automatic";
    requested_at: string;
  } | null;
};

const path = (courseId: string, lectureId: string) =>
  `/admin/courses/${encodeURIComponent(courseId)}/lectures/${encodeURIComponent(lectureId)}/canvas/change-request`;

/** Sections a change may be limited to; 409 explains why the lecture cannot change now. */
export function getCanvasChangeOptions(courseId: string, lectureId: string, session: LoginSession) {
  return apiRequest<CanvasChangeOptions>(
    session,
    path(courseId, lectureId),
    "The lecture's sections could not be loaded.",
  );
}

/**
 * Starts a background change request and returns once the server accepted it. Progress and
 * failures come from `lecture-states`, like every other draft.
 */
export async function requestCanvasChange(
  courseId: string,
  lectureId: string,
  input: { instruction: string; section_ids: readonly string[] },
  session: LoginSession,
) {
  await apiRequest(session, path(courseId, lectureId), "The change could not be requested.", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": globalThis.crypto.randomUUID(),
      Prefer: "respond-async",
    },
    body: JSON.stringify(input),
  });
}
