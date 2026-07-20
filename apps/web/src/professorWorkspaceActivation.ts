import type { CourseSetup, CourseWorkspaceState } from "./professorBuilderState";
import { lectureFromWorkspace } from "./professorWorkspaceView";
import type { Lecture, LectureScheduleItem, LoginSession, UniversityCourse } from "./types";

export function activationLectures(
  workspace: CourseWorkspaceState,
  setup: CourseSetup,
  schedule: LectureScheduleItem[],
): Lecture[] {
  if (setup.target === "full-course" && schedule.length) {
    return schedule.map(lectureFromScheduleItem);
  }
  return [lectureFromWorkspace(workspace, setup, schedule)];
}

export function courseFromSetup(
  courseId: string,
  setup: CourseSetup,
  session: LoginSession,
): UniversityCourse {
  return {
    access_policy: setup.accessPolicy,
    canvas_language: setup.canvasLanguage,
    id: courseId,
    professor: session.display_name ?? session.email ?? session.username,
    term: session.term,
    title: setup.courseTitle,
  };
}

export function lectureIdFromNumber(number: string) {
  const parsed = Number(number);
  return Number.isFinite(parsed)
    ? `lecture-${parsed.toString().padStart(2, "0")}`
    : `lecture-${number}`;
}

export function scheduleItemFromLecture(lecture: Lecture): LectureScheduleItem {
  return {
    date: lecture.date,
    material_path: lecture.materialPath,
    number: lecture.number,
    title: lecture.title,
  };
}

function lectureFromScheduleItem(lecture: LectureScheduleItem): Lecture {
  return {
    attendance: "unknown",
    date: lecture.date,
    id: lectureIdFromNumber(lecture.number),
    materialPath: lecture.material_path ?? undefined,
    number: lecture.number,
    title: lecture.title,
  };
}
