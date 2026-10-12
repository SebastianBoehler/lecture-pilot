import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import type { LoginSession } from "./types";

export type CourseInvite = { path: string };
export type CoursePreview = {
  title: string;
  term: string;
  lecture_count: number;
  canvas_language: "de" | "en";
};

async function call<T>(path: string, init: RequestInit, fallback: string): Promise<T> {
  const response = await fetch(apiUrl(path), init);
  if (response.status === 204) return undefined as T;
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readApiError(payload, fallback));
  return payload as T;
}

export function getCourseInvite(courseId: string, session: LoginSession) {
  return call<CourseInvite | null>(
    `/admin/courses/${courseId}/invite`,
    authRequestInit(session),
    "Course link failed to load.",
  );
}

export function rotateCourseInvite(courseId: string, session: LoginSession) {
  return call<CourseInvite>(
    `/admin/courses/${courseId}/invite`,
    authRequestInit(session, { method: "POST" }),
    "Course link could not be created.",
  );
}

export function disableCourseInvite(courseId: string, session: LoginSession) {
  return call<void>(
    `/admin/courses/${courseId}/invite`,
    authRequestInit(session, { method: "DELETE" }),
    "Course link could not be disabled.",
  );
}

export function previewCourseInvite(path: string) {
  return call<CoursePreview>(path, {}, "This course link is not valid.");
}

export function joinCourseInvite(path: string, session: LoginSession) {
  return call<{ course_id: string }>(
    path,
    authRequestInit(session, { method: "POST" }),
    "Joining the course failed.",
  );
}

export function inviteUrl(invite: CourseInvite) {
  return new URL(invite.path, window.location.origin).toString();
}

export function courseUrl(courseId: string) {
  return new URL(`/courses/${encodeURIComponent(courseId)}`, window.location.origin).toString();
}
