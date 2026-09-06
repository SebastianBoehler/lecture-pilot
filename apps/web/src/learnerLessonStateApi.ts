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

export function isLearnerLessonState(
  payload: unknown,
  courseId: string,
  lectureId: string,
): payload is LearnerLessonState {
  if (!payload || typeof payload !== "object") return false;
  const state = payload as Partial<LearnerLessonState>;
  return (
    state.course_id === courseId &&
    state.lecture_id === lectureId &&
    Number.isInteger(state.publication_version) &&
    Number(state.publication_version) >= 1 &&
    isRecord(state.gate_statuses) &&
    isRecord(state.quiz_states) &&
    (typeof state.active_session_goal === "string" || state.active_session_goal === null) &&
    (state.pending_check === null || isPendingCheck(state.pending_check)) &&
    Array.isArray(state.due_gate_reviews)
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

export async function requestCheckpointSupport(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  mode: LearnerWorkspaceMode,
  pending: NonNullable<LearnerLessonState["pending_check"]>,
): Promise<LearnerLessonState> {
  if (!pending.task_id || !pending.issued_at)
    throw new Error("Reload this lecture before requesting help.");
  const response = await fetch(
    apiUrl(`/courses/${courseId}/lectures/${lectureId}/learner-state/support`),
    learnerRequestInit(session, mode, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        gate_id: pending.gate_id,
        gate_revision: pending.gate_revision,
        task_id: pending.task_id,
        issued_at: pending.issued_at,
      }),
    }),
  );
  const payload: unknown = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Help could not be recorded."));
  if (!isLearnerLessonState(payload, courseId, lectureId))
    throw new Error("Help response is invalid.");
  return payload;
}

function isPendingCheck(value: unknown): boolean {
  if (!isRecord(value)) return false;
  return (
    typeof value.gate_id === "string" &&
    typeof value.gate_revision === "string" &&
    typeof value.prompt === "string" &&
    typeof value.task_id === "string" &&
    typeof value.issued_at === "string" &&
    typeof value.bank_exhausted === "boolean" &&
    [
      "diagnostic",
      "diagnostic_support",
      "independent_exit",
      "exit_support",
      "delayed_transfer",
      "delayed_support",
    ].includes(String(value.stage)) &&
    value.focus_required === ["independent_exit", "delayed_transfer"].includes(String(value.stage))
  );
}
