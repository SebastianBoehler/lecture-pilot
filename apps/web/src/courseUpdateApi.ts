import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import type {
  CourseUpdateAnalysis,
  CourseUpdateApplyResult,
  CourseUpdateLectureSelection,
} from "./courseUpdateTypes";
import type { LoginSession } from "./types";

export async function createCourseUpdate(courseId: string, session: LoginSession) {
  return request<{ course_id: string; update_id: string }>(
    `/admin/courses/${courseId}/updates`,
    session,
    { method: "POST" },
    "Course update could not be started.",
  );
}

export async function uploadCourseUpdateMaterial(input: {
  courseId: string;
  updateId: string;
  path: string;
  file: File;
  session: LoginSession;
}) {
  const body = new FormData();
  body.append("path", input.path);
  body.append("file", input.file);
  return request<{ path: string; kind: string; size_bytes: number }>(
    `/admin/courses/${input.courseId}/updates/${input.updateId}/materials`,
    input.session,
    { method: "POST", body },
    "Course update upload failed.",
  );
}

export async function getCourseUpdate(courseId: string, updateId: string, session: LoginSession) {
  return request<CourseUpdateAnalysis>(
    `/admin/courses/${courseId}/updates/${updateId}`,
    session,
    {},
    "Course update comparison failed.",
  );
}

export async function applyCourseUpdate(
  courseId: string,
  updateId: string,
  lectures: CourseUpdateLectureSelection[],
  session: LoginSession,
) {
  return request<CourseUpdateApplyResult>(
    `/admin/courses/${courseId}/updates/${updateId}/apply`,
    session,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lectures }),
    },
    "Course update could not be applied.",
  );
}

export async function discardCourseUpdate(
  courseId: string,
  updateId: string,
  session: LoginSession,
) {
  const response = await fetch(
    apiUrl(`/admin/courses/${courseId}/updates/${updateId}`),
    authRequestInit(session, { method: "DELETE" }),
  );
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(readApiError(payload, "Course update could not be discarded."));
  }
}

async function request<T>(
  path: string,
  session: LoginSession,
  init: RequestInit,
  fallback: string,
): Promise<T> {
  const response = await fetch(apiUrl(path), authRequestInit(session, init));
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readApiError(payload, fallback));
  return payload as T;
}
