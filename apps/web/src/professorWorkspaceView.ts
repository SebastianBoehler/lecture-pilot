import type { CourseSetup, CourseWorkspaceState } from "./professorBuilderState";
import type { Lecture } from "./types";

export function requireWorkspace(workspace: CourseWorkspaceState | null): CourseWorkspaceState {
  if (!workspace) throw new Error("Create the course workspace first.");
  return workspace;
}

export function lectureFromWorkspace(workspace: CourseWorkspaceState, setup: CourseSetup): Lecture {
  return {
    id: workspace.lectureId,
    number: setup.lectureNumber || "01",
    title: setup.lectureTitle || "Lecture",
    date: "Draft",
    attendance: "unknown",
  };
}
