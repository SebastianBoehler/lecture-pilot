import { apiUrl } from "./api";
import { authRequestInit } from "./authz";
import type { Attendance, LectureAnalyticsSummary, LoginSession } from "./types";

export async function recordQuizAnswer(input: {
  courseId: string;
  lectureId: string;
  attendance: Attendance;
  blockId: string;
  optionIndex: number;
  session: LoginSession;
}) {
  const response = await analyticsFetch(
    apiUrl(`/courses/${input.courseId}/lectures/${input.lectureId}/analytics/quiz-answer`),
    authRequestInit(input.session, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        attendance: input.attendance,
        block_id: input.blockId,
        option_index: input.optionIndex,
      }),
    }),
  );
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Quiz analytics recording failed."));
  return payload as { correct: boolean | null };
}

export async function getLectureAnalytics(
  courseId: string,
  lectureId: string,
  session: LoginSession,
): Promise<LectureAnalyticsSummary> {
  const response = await analyticsFetch(
    apiUrl(`/admin/courses/${courseId}/lectures/${lectureId}/analytics`),
    authRequestInit(session),
  );
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Lecture analytics loading failed."));
  return payload as LectureAnalyticsSummary;
}

async function analyticsFetch(url: string, init: RequestInit) {
  try {
    return await fetch(url, init);
  } catch {
    throw new Error("Cannot reach the local LecturePilot API. Is the backend running?");
  }
}

function readApiError(payload: unknown, fallback: string) {
  return typeof (payload as { detail?: unknown }).detail === "string"
    ? String((payload as { detail: string }).detail)
    : fallback;
}
