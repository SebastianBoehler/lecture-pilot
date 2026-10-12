import { apiRequest } from "./apiRequest";
import type {
  LearningDesignApprovalInput,
  LearningDesignReview,
  LearningDesignUpdate,
} from "./learningDesignTypes";
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
  const approval: LearningDesignApprovalInput = {
    draft_digest: review.draft_digest,
    source_revision: review.source_revision,
    practice_design_revision: review.practice_design_revision,
    learning_map_revision: review.learning_map.revision,
    report_revision: review.report.report_revision,
  };
  return request(`${path(courseId, lectureId)}/approve`, session, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(approval),
  });
}

async function request(
  requestPath: string,
  session: LoginSession,
  init?: RequestInit,
): Promise<LearningDesignReview> {
  return apiRequest<LearningDesignReview>(
    session,
    requestPath,
    "Learning-design review failed.",
    init,
  );
}
