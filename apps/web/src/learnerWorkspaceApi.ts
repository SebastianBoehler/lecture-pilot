import { learnerRequestInit } from "./authz";
import { apiUrl, readApiError } from "./api";
import type { Attendance, LearnerWorkspaceMode, LoginSession } from "./types";

export type LearnerWorkspaceResetOptions = {
  reset_canvas: boolean;
  reset_course_memory: boolean;
  reset_progress: boolean;
};

export type LearnerWorkspaceResetResult = LearnerWorkspaceResetOptions & {
  course_id: string;
  deleted_paths: number;
};

export async function resetLearnerWorkspace(
  courseId: string,
  options: LearnerWorkspaceResetOptions,
  session: LoginSession,
  mode: LearnerWorkspaceMode = "learner",
): Promise<LearnerWorkspaceResetResult> {
  const response = await fetch(
    apiUrl(`/courses/${courseId}/learner-workspace/reset`),
    learnerRequestInit(session, mode, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(options),
    }),
  );
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readApiError(payload, "Workspace reset failed."));
  return payload as LearnerWorkspaceResetResult;
}

export async function saveLectureAttendance(
  courseId: string,
  lectureId: string,
  attendance: Attendance,
  session: LoginSession,
): Promise<void> {
  const response = await fetch(
    apiUrl(`/courses/${courseId}/lectures/${lectureId}/attendance`),
    learnerRequestInit(session, "learner", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ attendance }),
    }),
  );
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(readApiError(payload, "Attendance could not be saved."));
  }
}
