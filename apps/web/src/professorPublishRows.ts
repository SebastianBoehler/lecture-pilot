import type { CourseSetup } from "./professorBuilderState";
import type { Lecture, LectureScheduleItem } from "./types";

export type PublishLectureRow = {
  id: string;
  label: string;
  previewHref: string;
  published: boolean;
};

export function publishLectureRows({
  courseId,
  lectureSchedule,
  previewWorkspaceUrl,
  publishedLectureIds,
  setup,
  workspaceLecture,
}: {
  courseId: string;
  lectureSchedule: LectureScheduleItem[];
  previewWorkspaceUrl: (courseId: string, lecture: Lecture) => string;
  publishedLectureIds: string[];
  setup: CourseSetup;
  workspaceLecture: Lecture;
}): PublishLectureRow[] {
  const lectures = setup.target === "full-course" && lectureSchedule.length
    ? lectureSchedule.map(lectureFromScheduleItem)
    : [workspaceLecture];
  return lectures.map((lecture) => ({
    id: lecture.id,
    label: `${lecture.number} · ${lecture.title}`,
    previewHref: previewWorkspaceUrl(courseId, lecture),
    published: publishedLectureIds.includes(lecture.id),
  }));
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

function lectureIdFromNumber(number: string) {
  const parsed = Number(number);
  return Number.isFinite(parsed) ? `lecture-${parsed.toString().padStart(2, "0")}` : `lecture-${number}`;
}
