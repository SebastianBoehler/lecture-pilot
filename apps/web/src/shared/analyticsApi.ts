import { apiUrl } from "./api";
import { authRequestInit, learnerRequestInit } from "./authz";
import type {
  Attendance,
  CourseAnalyticsSummary,
  LearnerWorkspaceMode,
  LectureAnalyticsSummary,
  LoginSession,
} from "./types";

export type LearnerQuizAnswerResult = {
  block_id: string;
  selected_index: number;
  correct: boolean | null;
  publication_version: number;
  attempt_index: number;
  first_attempt_correct: boolean | null;
  latest_outcome: "correct" | "incorrect" | "unscored";
  correction_state: "not_needed" | "needed" | "corrected";
  feedback: string;
};

export class StaleQuizPublicationError extends Error {}

type QuizAnswerPayloadInput = {
  attendance: Attendance;
  attemptId: string;
  blockId: string;
  optionIndex: number;
  publicationVersion: number;
};

export async function getCourseAnalytics(
  courseId: string,
  session: LoginSession,
): Promise<CourseAnalyticsSummary> {
  const response = await analyticsFetch(
    apiUrl(`/admin/courses/${courseId}/analytics`),
    authRequestInit(session),
  );
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Course analytics loading failed."));
  return payload as CourseAnalyticsSummary;
}

export async function recordQuizAnswer(input: {
  courseId: string;
  lectureId: string;
  attendance: Attendance;
  attemptId: string;
  blockId: string;
  optionIndex: number;
  publicationVersion: number;
  session: LoginSession;
  mode?: LearnerWorkspaceMode;
}) {
  const response = await analyticsFetch(
    apiUrl(`/courses/${input.courseId}/lectures/${input.lectureId}/analytics/quiz-answer`),
    learnerRequestInit(input.session, input.mode ?? "learner", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(quizAnswerPayload(input)),
    }),
  );
  const payload = await response.json();
  if (!response.ok) throw quizSubmissionError(response.status, payload);
  return payload as LearnerQuizAnswerResult;
}

export function quizAnswerPayload(input: QuizAnswerPayloadInput) {
  return {
    attendance: input.attendance,
    attempt_id: input.attemptId,
    block_id: input.blockId,
    option_index: input.optionIndex,
    publication_version: input.publicationVersion,
  };
}

export function quizSubmissionError(status: number, payload: unknown): Error {
  const detail = (payload as { detail?: unknown })?.detail;
  if (
    status === 409 &&
    detail &&
    typeof detail === "object" &&
    (detail as { code?: unknown }).code === "stale_quiz_publication" &&
    typeof (detail as { message?: unknown }).message === "string"
  ) {
    return new StaleQuizPublicationError((detail as { message: string }).message);
  }
  return new Error(readApiError(payload, "Quiz analytics recording failed."));
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
