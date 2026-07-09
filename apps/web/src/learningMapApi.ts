import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import type { LearningMap } from "./learningMapTypes";
import type { LoginSession } from "./types";

export async function getLectureLearningMap(
  courseId: string,
  lectureId: string,
  session: LoginSession,
): Promise<LearningMap> {
  const response = await fetch(
    apiUrl(`/courses/${courseId}/lectures/${lectureId}/learning-map`),
    authRequestInit(session),
  );
  const payload = await response.json();
  if (!response.ok) throw new Error(readApiError(payload, "Learning path loading failed."));
  return payload as LearningMap;
}
