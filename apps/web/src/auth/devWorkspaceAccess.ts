import { localDemoSession } from "../shell/appDefaults";
import type { UniversityCourse } from "../shared/types";

export function developmentWorkspaceCourse(): UniversityCourse | null {
  return import.meta.env.DEV ? localDemoSession.courses[0] : null;
}

export function hasDevelopmentWorkspaceAccess(course: UniversityCourse) {
  return developmentWorkspaceCourse()?.id === course.id;
}
