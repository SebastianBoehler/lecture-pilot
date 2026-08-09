import { apiUrl, readApiError } from "./api";
import { learnerRequestInit } from "./authz";
import type { LearnerLessonState } from "./learnerLessonStateTypes";
import type { LearnerWorkspaceMode, LoginSession } from "./types";

export async function getLearnerLessonState(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  mode: LearnerWorkspaceMode,
): Promise<LearnerLessonState> {
  const response = await fetch(
    apiUrl(`/courses/${courseId}/lectures/${lectureId}/learner-state`),
    learnerRequestInit(session, mode),
  );
  const payload: unknown = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Learner state loading failed."));
  if (!isLearnerLessonState(payload, courseId, lectureId)) {
    throw new Error("Learner state response is invalid.");
  }
  return payload;
}

function isLearnerLessonState(
  payload: unknown,
  courseId: string,
  lectureId: string,
): payload is LearnerLessonState {
  if (!payload || typeof payload !== "object") return false;
  const state = payload as Partial<LearnerLessonState>;
  return (
    state.course_id === courseId &&
    state.lecture_id === lectureId &&
    isRecord(state.gate_statuses) &&
    isRecord(state.quiz_states) &&
    (typeof state.active_session_goal === "string" || state.active_session_goal === null) &&
    (typeof state.pending_check === "object" || state.pending_check === null) &&
    Array.isArray(state.due_gate_reviews)
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}
