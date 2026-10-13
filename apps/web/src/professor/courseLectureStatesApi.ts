import { apiRequest } from "../shared/apiRequest";
import type { CourseLectureStates } from "./courseLectureStateTypes";
import type { PracticeDesign } from "./practiceDesignTypes";
import type { LoginSession } from "../shared/types";

const enc = encodeURIComponent;

export function getCourseLectureStates(courseId: string, session: LoginSession) {
  return apiRequest<CourseLectureStates>(
    session,
    `/admin/courses/${enc(courseId)}/lecture-states`,
    "Lecture states could not be loaded.",
  );
}

/** Keeps approved goals after a source change; the backend answers 409 when not applicable. */
export function keepLearningGoals(courseId: string, lectureId: string, session: LoginSession) {
  return apiRequest<PracticeDesign>(
    session,
    `/admin/courses/${enc(courseId)}/lectures/${enc(lectureId)}/practice-design/intent/keep`,
    "Learning goals could not be kept.",
    { method: "POST" },
  );
}

/**
 * Starts a background draft and returns once the server accepted it. Progress and failures come
 * from `lecture-states`, so this never waits for the generation itself.
 */
export async function startLectureDraft(
  courseId: string,
  lectureId: string,
  session: LoginSession,
) {
  await apiRequest(
    session,
    `/admin/courses/${enc(courseId)}/lectures/${enc(lectureId)}/canvas/draft`,
    "Draft generation could not be started.",
    {
      method: "POST",
      headers: { "Idempotency-Key": globalThis.crypto.randomUUID(), Prefer: "respond-async" },
    },
  );
}
