import type { CourseSetup, CourseWorkspaceState } from "./professorBuilderState";
import type { Lecture, LectureScheduleItem } from "./types";

export function requireWorkspace(workspace: CourseWorkspaceState | null): CourseWorkspaceState {
  if (!workspace) throw new Error("Create the course workspace first.");
  return workspace;
}

export function lectureFromWorkspace(
  workspace: CourseWorkspaceState,
  setup: CourseSetup,
  schedule: LectureScheduleItem[] = [],
): Lecture {
  const scheduled = schedule.find((lecture) => lectureIdFromNumber(lecture.number) === workspace.lectureId);
  return {
    id: workspace.lectureId,
    number: scheduled?.number ?? setup.lectureNumber ?? "01",
    title: scheduled?.title ?? setup.lectureTitle ?? "Lecture",
    date: scheduled?.date ?? "Draft",
    attendance: "unknown",
    materialPath: scheduled?.material_path ?? undefined,
  };
}

function lectureIdFromNumber(number: string) {
  const parsed = Number(number);
  return Number.isFinite(parsed) ? `lecture-${parsed.toString().padStart(2, "0")}` : `lecture-${number}`;
}
