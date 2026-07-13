import type { Attendance, CourseWorkspaceResult, Lecture } from "./types";

type ApiLecture = {
  id: string;
  title: string;
  date: string;
  material_path?: string | null;
};

type ApiLectureView = {
  lecture: ApiLecture;
  attendance?: Attendance;
};

type ApiCourseWorkspaceResult = Omit<CourseWorkspaceResult, "lectures"> & {
  lectures: ApiLecture[];
  published_lecture_ids?: string[];
};

export function normalizeCourseWorkspaceResult(payload: ApiCourseWorkspaceResult): CourseWorkspaceResult {
  return {
    ...payload,
    lectures: payload.lectures.map((lecture) => lectureFromApi(lecture)),
    publishedLectureIds: payload.published_lecture_ids ?? payload.publishedLectureIds ?? [],
  };
}

export function normalizeLectureList(payload: Array<ApiLecture | ApiLectureView>): Lecture[] {
  return payload.map((item) => {
    if ("lecture" in item) {
      return lectureFromApi(item.lecture, item.attendance);
    }
    return lectureFromApi(item);
  });
}

function lectureFromApi(lecture: ApiLecture, attendance: Attendance = "unknown"): Lecture {
  return {
    id: lecture.id,
    number: lectureNumber(lecture.id),
    title: lecture.title,
    date: lecture.date,
    attendance,
    materialPath: lecture.material_path ?? undefined,
  };
}

function lectureNumber(lectureId: string) {
  const match = lectureId.match(/(\d+)$/);
  return match ? match[1].padStart(2, "0") : lectureId.replace(/^lecture-/, "");
}
