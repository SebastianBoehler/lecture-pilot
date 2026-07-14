import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import type { CourseAccessRule } from "./courseAccessTypes";
import type { LoginSession } from "./types";

type AccessRequest = {
  confirmUniversityMembers: boolean;
  courseId: string;
  rule: CourseAccessRule;
  session: LoginSession;
};

export async function updateCourseAccess(input: AccessRequest) {
  return writeAccess(`/admin/courses/${encodeURIComponent(input.courseId)}/access`, input);
}

export async function updateLectureAccess(input: AccessRequest & { lectureId: string }) {
  return writeAccess(
    `/admin/courses/${encodeURIComponent(input.courseId)}/lectures/${encodeURIComponent(input.lectureId)}/access`,
    input,
  );
}

export async function deleteLectureAccess(input: {
  courseId: string;
  lectureId: string;
  session: LoginSession;
}) {
  const response = await fetch(
    apiUrl(
      `/admin/courses/${encodeURIComponent(input.courseId)}/lectures/${encodeURIComponent(input.lectureId)}/access`,
    ),
    authRequestInit(input.session, { method: "DELETE" }),
  );
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readApiError(payload, "Access settings could not be saved."));
  return payload;
}

async function writeAccess(path: string, input: AccessRequest) {
  const response = await fetch(
    apiUrl(path),
    authRequestInit(input.session, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rule: input.rule,
        confirm_university_members: input.confirmUniversityMembers,
      }),
    }),
  );
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readApiError(payload, "Access settings could not be saved."));
  return payload;
}
