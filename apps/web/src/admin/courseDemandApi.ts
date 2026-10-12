import { apiRequest } from "../shared/apiRequest";
import type { UniversityEnrollmentCourse } from "../auth/universityCourseTypes";
import type { LoginSession } from "../shared/types";

/** Aggregate demand for one Alma/ILIAS course; the backend never returns account identities. */
export type CourseDemandRow = Pick<
  UniversityEnrollmentCourse,
  "source" | "external_course_id" | "term" | "title"
> & {
  number: string | null;
  organization: string | null;
  instructor: string | null;
  display_url: string | null;
  request_count: number;
  enrolled_user_count: number;
  has_workspace: boolean;
  first_requested_at: string | null;
  last_requested_at: string | null;
};

export async function getCourseDemand(session: LoginSession) {
  const payload = await apiRequest(
    session,
    "/platform/course-support-demand",
    "Course demand could not be loaded.",
  );
  if (!isRecord(payload) || !Array.isArray(payload.items) || !payload.items.every(isRow)) {
    throw new Error("Course demand response is invalid.");
  }
  return payload.items as CourseDemandRow[];
}

function isRow(value: unknown): value is CourseDemandRow {
  return (
    isRecord(value) &&
    (value.source === "alma" || value.source === "ilias") &&
    typeof value.external_course_id === "string" &&
    typeof value.term === "string" &&
    typeof value.title === "string" &&
    typeof value.request_count === "number" &&
    typeof value.enrolled_user_count === "number" &&
    typeof value.has_workspace === "boolean" &&
    ["number", "organization", "instructor", "display_url"].every((key) =>
      optionalString(value[key]),
    ) &&
    optionalString(value.first_requested_at) &&
    optionalString(value.last_requested_at)
  );
}

function optionalString(value: unknown) {
  return value === null || value === undefined || typeof value === "string";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
