import type { UniversityCourse } from "./types";

const demoWorkspaceKey = "lecturepilot.demo.workspaceCourse";

export function readDemoWorkspaceCourse(): UniversityCourse | null {
  try {
    const saved = window.localStorage.getItem(demoWorkspaceKey);
    return saved ? JSON.parse(saved) as UniversityCourse : null;
  } catch {
    return null;
  }
}

export function writeDemoWorkspaceCourse(course: UniversityCourse) {
  try {
    window.localStorage.setItem(demoWorkspaceKey, JSON.stringify(course));
  } catch {
  }
}
