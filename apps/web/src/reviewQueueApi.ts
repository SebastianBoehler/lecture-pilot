import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import type {
  CourseReviewQueue,
  GateReviewOpening,
  GateReviewQueueItem,
  ReviewQueueItem,
} from "./reviewQueueTypes";
import type { LoginSession } from "./types";

export async function getReviewQueue(courseId: string, session: LoginSession) {
  const response = await fetch(
    apiUrl(`/courses/${courseId}/review-queue`),
    authRequestInit(session),
  );
  const payload: unknown = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Review queue loading failed."));
  if (!isReviewQueue(payload, courseId)) throw new Error("Review queue response is invalid.");
  return payload;
}

export async function openGateReview(item: GateReviewQueueItem, session: LoginSession) {
  const response = await fetch(
    apiUrl(`/courses/${item.course_id}/review-queue/gates/${item.lecture_id}/${item.gate_id}/open`),
    authRequestInit(session, { method: "POST" }),
  );
  const payload: unknown = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Gate review opening failed."));
  if (!isGateOpening(payload, item)) throw new Error("Gate review opening response is invalid.");
  return payload;
}

function isReviewQueue(payload: unknown, courseId: string): payload is CourseReviewQueue {
  if (!isRecord(payload) || payload.course_id !== courseId || !Array.isArray(payload.items)) {
    return false;
  }
  return payload.items.every((item) => isQueueItem(item, courseId));
}

function isQueueItem(value: unknown, courseId: string): value is ReviewQueueItem {
  if (!isRecord(value) || value.course_id !== courseId) return false;
  if (!hasStrings(value, ["id", "lecture_id", "lecture_title", "section_id", "section_title"])) {
    return false;
  }
  if (value.kind === "readiness_repair") {
    return hasStrings(value, ["task_id", "next_action"]);
  }
  return (
    (value.kind === "gate_review" || value.kind === "gate_repair") &&
    hasStrings(value, ["gate_id", "gate_revision", "due_at"])
  );
}

function isGateOpening(value: unknown, item: GateReviewQueueItem): value is GateReviewOpening {
  return (
    isRecord(value) &&
    value.course_id === item.course_id &&
    value.lecture_id === item.lecture_id &&
    value.gate_id === item.gate_id &&
    value.gate_revision === item.gate_revision &&
    value.section_id === item.section_id &&
    typeof value.prompt === "string" &&
    (value.stage === "due" || value.stage === "repair")
  );
}

function hasStrings(value: Record<string, unknown>, keys: string[]) {
  return keys.every((key) => typeof value[key] === "string" && value[key].length > 0);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}
