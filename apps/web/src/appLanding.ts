import { canManageCourses } from "./authz";
import type { LoginSession, View } from "./types";

export type LandingView = Exclude<View, "lesson" | "course-link">;

export function landingView(session: LoginSession | null): LandingView {
  if (!session) return "login";
  if ((session.account_type ?? "student") === "professor") {
    return canManageCourses(session) ? "professor" : "profile";
  }
  return "dashboard";
}
