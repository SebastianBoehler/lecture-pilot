import { apiRequest } from "../shared/apiRequest";
import type {
  CourseUpdateAnalysis,
  CourseUpdateApplyResult,
  CourseUpdateLectureSelection,
} from "./courseUpdateTypes";
import type { LoginSession } from "../shared/types";

const base = (courseId: string) => `/admin/courses/${encodeURIComponent(courseId)}/updates`;

export function createCourseUpdate(courseId: string, session: LoginSession) {
  return apiRequest<{ course_id: string; update_id: string }>(
    session,
    base(courseId),
    "Course update could not be started.",
    { method: "POST" },
  );
}

export function uploadCourseUpdateMaterial(input: {
  courseId: string;
  updateId: string;
  path: string;
  file: File;
  session: LoginSession;
}) {
  const body = new FormData();
  body.append("path", input.path);
  body.append("file", input.file);
  return apiRequest<{ path: string; kind: string; size_bytes: number }>(
    input.session,
    `${base(input.courseId)}/${input.updateId}/materials`,
    "Course update upload failed.",
    { method: "POST", body },
  );
}

export function getCourseUpdate(courseId: string, updateId: string, session: LoginSession) {
  return apiRequest<CourseUpdateAnalysis>(
    session,
    `${base(courseId)}/${updateId}`,
    "Course update comparison failed.",
  );
}

/** Applies the reviewed update; the backend routes its files and proposes goals for new lectures. */
export function applyCourseUpdate(
  courseId: string,
  updateId: string,
  lectures: CourseUpdateLectureSelection[],
  session: LoginSession,
) {
  return apiRequest<CourseUpdateApplyResult>(
    session,
    `${base(courseId)}/${updateId}/apply`,
    "Course update could not be applied.",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lectures }),
    },
  );
}

export async function discardCourseUpdate(
  courseId: string,
  updateId: string,
  session: LoginSession,
) {
  await apiRequest(
    session,
    `${base(courseId)}/${updateId}`,
    "Course update could not be discarded.",
    { method: "DELETE" },
  );
}
