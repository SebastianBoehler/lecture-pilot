import { apiRequest } from "./apiRequest";
import type { LearnerProfile, LearningGoal, LoginSession } from "./types";

export async function getLearnerProfile(session: LoginSession): Promise<LearnerProfile> {
  return profileRequest(session, "/me/learning-profile");
}

export async function saveLearnerCalibration(
  session: LoginSession,
  learningGoal: LearningGoal,
): Promise<LearnerProfile> {
  return profileRequest(session, "/me/learning-profile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ learning_goal: learningGoal, onboarding_completed: true }),
  });
}

export async function removeLearnerPreference(session: LoginSession, key: string): Promise<void> {
  await emptyProfileRequest(session, `/me/learning-profile/preferences/${encodeURIComponent(key)}`);
}

export async function clearLearnerMemory(session: LoginSession, courseId?: string): Promise<void> {
  const query = courseId ? `?course_id=${encodeURIComponent(courseId)}` : "";
  await emptyProfileRequest(session, `/me/learning-profile/memory${query}`);
}

async function profileRequest(
  session: LoginSession,
  path: string,
  init: RequestInit = {},
): Promise<LearnerProfile> {
  const payload = await apiRequest(session, path, "Learning profile request failed.", init);
  if (!isLearnerProfile(payload)) throw new Error("Learning profile response was invalid.");
  return payload;
}

function isLearnerProfile(payload: unknown): payload is LearnerProfile {
  if (!payload || typeof payload !== "object") return false;
  const candidate = payload as Partial<LearnerProfile>;
  return (
    typeof candidate.onboarding_completed === "boolean" &&
    Array.isArray(candidate.courses) &&
    Array.isArray(candidate.global_files) &&
    Boolean(candidate.preferences && typeof candidate.preferences === "object") &&
    typeof candidate.global_notes === "string"
  );
}

async function emptyProfileRequest(session: LoginSession, path: string): Promise<void> {
  await apiRequest(session, path, "Learning profile update failed.", { method: "DELETE" });
}
