import type { UniversityCourse } from "./types";

const demoWorkspaceKey = "lecturepilot.demo.workspaceCourse";

export function readDemoWorkspaceCourse(): UniversityCourse | null {
  if (!import.meta.env.DEV) return null;
  try {
    const saved = window.localStorage.getItem(demoWorkspaceKey);
    return saved ? JSON.parse(saved) as UniversityCourse : null;
  } catch {
    return null;
  }
}

export function writeDemoWorkspaceCourse(course: UniversityCourse) {
  if (!import.meta.env.DEV) return;
  try {
    window.localStorage.setItem(demoWorkspaceKey, JSON.stringify(course));
  } catch {
  }
}

export function clearDemoWorkspaceCourse(courseId?: string) {
  if (!import.meta.env.DEV) return;
  try {
    if (!courseId) {
      window.localStorage.removeItem(demoWorkspaceKey);
      return;
    }
    const saved = readDemoWorkspaceCourse();
    if (saved?.id === courseId) window.localStorage.removeItem(demoWorkspaceKey);
  } catch {
  }
}
