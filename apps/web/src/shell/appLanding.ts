import { canManageCourses } from "../shared/authz";
import type { LoginSession, View } from "../shared/types";

export type LandingView = Exclude<View, "lesson" | "course-link">;

/** Landing view known without a request; course managers resolve theirs asynchronously. */
export function landingView(session: LoginSession | null): LandingView {
  if (!session) return "login";
  if ((session.account_type ?? "student") === "professor") {
    return canManageCourses(session) ? "professor" : "profile";
  }
  return "dashboard";
}

/** Professors who already manage courses land on course management, others in the builder. */
export async function resolveLandingView(session: LoginSession | null): Promise<LandingView> {
  const view = landingView(session);
  if (view !== "professor" || !session) return view;
  // Loaded on demand so student bundles never include professor course APIs.
  const { listCourseWorkspaces } = await import("../professor/professorApi");
  try {
    const workspaces = await listCourseWorkspaces(session);
    return workspaces.length ? "course-management" : "professor";
  } catch {
    // Course management shows the loading error and still offers course creation.
    return "course-management";
  }
}
