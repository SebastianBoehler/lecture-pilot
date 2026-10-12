import { apiRequest } from "../shared/apiRequest";
import type { UniversityEnrollmentCourse } from "../auth/universityCourseTypes";
import type { LoginSession } from "../shared/types";

/** One of the learner's own Alma/ILIAS courses; the backend checks it against stored observations. */
export type CourseSupportKey = Pick<
  UniversityEnrollmentCourse,
  "source" | "external_course_id" | "term"
>;

export type CourseSupportStatus = CourseSupportKey & {
  requested: boolean;
  /** Distinct accounts that asked, including the learner when `requested` is true. */
  request_count: number;
};

const ROUTE = "/me/course-support-requests";

export function courseSupportKeyId(key: CourseSupportKey) {
  return `${key.source}\u0000${key.external_course_id}\u0000${key.term}`;
}

export async function getCourseSupportRequests(session: LoginSession) {
  const payload = await apiRequest(session, ROUTE, "Course requests could not be loaded.");
  if (!isRecord(payload) || !Array.isArray(payload.items) || !payload.items.every(isStatus)) {
    throw new Error("Course request response is invalid.");
  }
  return payload.items as CourseSupportStatus[];
}

export async function setCourseSupportRequest(
  session: LoginSession,
  key: CourseSupportKey,
  requested: boolean,
) {
  const payload = await apiRequest(session, ROUTE, "Course request could not be saved.", {
    method: requested ? "PUT" : "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source: key.source,
      external_course_id: key.external_course_id,
      term: key.term,
    }),
  });
  if (!isStatus(payload) || courseSupportKeyId(payload) !== courseSupportKeyId(key)) {
    throw new Error("Course request response is invalid.");
  }
  return payload;
}

function isStatus(value: unknown): value is CourseSupportStatus {
  return (
    isRecord(value) &&
    (value.source === "alma" || value.source === "ilias") &&
    typeof value.external_course_id === "string" &&
    typeof value.term === "string" &&
    typeof value.requested === "boolean" &&
    typeof value.request_count === "number" &&
    value.request_count >= 0
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
