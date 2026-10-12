import { apiUrl, readApiError } from "./api";
import { authRequestInit, learnerRequestInit } from "./authz";
import type { LearnerWorkspaceMode, LoginSession } from "./types";

export type CourseSearchHit = {
  lecture_id: string;
  lecture_title: string;
  section_id: string;
  section_title: string;
  snippet: string;
};

export type CourseSearchResult = { results: CourseSearchHit[]; truncated: boolean };

export type CourseVisit = { course_id: string; new_lecture_ids: string[] };

export const MIN_SEARCH_LENGTH = 2;
export const MAX_SEARCH_LENGTH = 100;

function coursePath(courseId: string, suffix: string) {
  return apiUrl(`/courses/${encodeURIComponent(courseId)}${suffix}`);
}

export async function searchCourse(
  courseId: string,
  query: string,
  session: LoginSession,
  signal?: AbortSignal,
): Promise<CourseSearchResult> {
  const response = await fetch(
    coursePath(courseId, `/search?${new URLSearchParams({ q: query })}`),
    authRequestInit(session, { signal }),
  );
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readApiError(payload, "Search failed."));
  if (!isSearchResult(payload)) throw new Error("Search response is invalid.");
  return payload;
}

export async function recordCourseVisit(
  courseId: string,
  session: LoginSession,
): Promise<CourseVisit | null> {
  const response = await fetch(
    coursePath(courseId, "/visits"),
    authRequestInit(session, { method: "POST" }),
  );
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readApiError(payload, "Visit could not be recorded."));
  return isCourseVisit(payload, courseId) ? payload : null;
}

export async function recordLectureVisit(
  courseId: string,
  lectureId: string,
  session: LoginSession,
): Promise<void> {
  const response = await fetch(
    coursePath(courseId, `/lectures/${encodeURIComponent(lectureId)}/visits`),
    authRequestInit(session, { method: "POST" }),
  );
  if (!response.ok) throw new Error("Lecture visit could not be recorded.");
}

export async function downloadLectureNotes(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  mode: LearnerWorkspaceMode = "learner",
): Promise<void> {
  const response = await fetch(
    coursePath(courseId, `/lectures/${encodeURIComponent(lectureId)}/notes.md`),
    learnerRequestInit(session, mode),
  );
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(readApiError(payload, "Notes export failed."));
  }
  const url = URL.createObjectURL(await response.blob());
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `lecturepilot-notes-${lectureId.replace(/[^A-Za-z0-9._-]+/g, "-")}.md`;
    anchor.click();
  } finally {
    URL.revokeObjectURL(url);
  }
}

function isSearchResult(value: unknown): value is CourseSearchResult {
  if (!isRecord(value) || !Array.isArray(value.results) || typeof value.truncated !== "boolean") {
    return false;
  }
  return value.results.every(
    (item) =>
      isRecord(item) &&
      ["lecture_id", "lecture_title", "section_id", "section_title", "snippet"].every(
        (key) => typeof item[key] === "string",
      ),
  );
}

function isCourseVisit(value: unknown, courseId: string): value is CourseVisit {
  return (
    isRecord(value) &&
    value.course_id === courseId &&
    Array.isArray(value.new_lecture_ids) &&
    value.new_lecture_ids.every((item) => typeof item === "string")
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}
