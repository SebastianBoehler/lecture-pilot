import { localDemoSession } from "./appDefaults";
import type { UniversityCourse } from "./types";

export function developmentWorkspaceCourse(): UniversityCourse | null {
  return import.meta.env.DEV ? localDemoSession.courses[0] : null;
}

export function hasDevelopmentWorkspaceAccess(course: UniversityCourse) {
  return developmentWorkspaceCourse()?.id === course.id;
}
