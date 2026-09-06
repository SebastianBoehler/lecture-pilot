import { apiUrl } from "./api";
import { readApiError } from "./apiError";
import { authRequestInit } from "./authz";
import type { PracticeExamAnswers } from "./practiceExamTypes";
import type { LoginSession } from "./types";

export type PracticeAttempt = {
  id: string;
  exam_id: string;
  course_id: string;
  created_at: string;
  answers: PracticeExamAnswers;
  assessment: "ungraded";
  assistance: "unknown";
};

async function request<T>(
  courseId: string,
  examId: string,
  session: LoginSession,
  options: RequestInit = {},
  suffix = "",
): Promise<T> {
  const response = await fetch(
    apiUrl(
      `/courses/${encodeURIComponent(courseId)}/practice-exams/${encodeURIComponent(examId)}/attempts${suffix}`,
    ),
    authRequestInit(session, {
      ...options,
      headers: { "Content-Type": "application/json" },
    }),
  );
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readApiError(payload, "Could not access saved attempts."));
  return payload as T;
}

export const listPracticeAttempts = (courseId: string, examId: string, session: LoginSession) =>
  request<PracticeAttempt[]>(courseId, examId, session);
export const savePracticeAttempt = (
  courseId: string,
  examId: string,
  session: LoginSession,
  submission: { id: string; answers: PracticeExamAnswers },
) =>
  request<PracticeAttempt>(courseId, examId, session, {
    method: "POST",
    body: JSON.stringify(submission),
  });
export const deletePracticeAttempt = (
  courseId: string,
  examId: string,
  session: LoginSession,
  id: string,
) =>
  request<{ deleted: boolean }>(
    courseId,
    examId,
    session,
    { method: "DELETE" },
    `/${encodeURIComponent(id)}`,
  );
