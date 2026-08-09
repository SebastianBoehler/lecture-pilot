import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import type { LearningDesignReview, LearningDesignUpdate } from "./learningDesignTypes";
import type { LoginSession } from "./types";

function path(courseId: string, lectureId: string) {
  return `/admin/courses/${courseId}/lectures/${lectureId}/canvas/learning-design`;
}

export async function getLearningDesignReview(
  courseId: string,
  lectureId: string,
  session: LoginSession,
): Promise<LearningDesignReview> {
  return request(path(courseId, lectureId), session);
}

export async function saveLearningDesignReview(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  update: LearningDesignUpdate,
): Promise<LearningDesignReview> {
  return request(path(courseId, lectureId), session, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  });
}

export async function approveLearningDesignReview(
  courseId: string,
  lectureId: string,
  session: LoginSession,
  review: LearningDesignReview,
): Promise<LearningDesignReview> {
  return request(`${path(courseId, lectureId)}/approve`, session, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      draft_digest: review.draft_digest,
      source_revision: review.source_revision,
    }),
  });
}

async function request(
  requestPath: string,
  session: LoginSession,
  init?: RequestInit,
): Promise<LearningDesignReview> {
  const response = await fetch(apiUrl(requestPath), authRequestInit(session, init));
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readApiError(payload, "Learning-design review failed."));
  return payload as LearningDesignReview;
}
