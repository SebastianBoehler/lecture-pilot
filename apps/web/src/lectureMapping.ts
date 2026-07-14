import type {
  CourseAccessRule,
  CourseAccessSummary,
  LectureReleaseStatus,
} from "./courseAccessTypes";
import type {
  Attendance,
  CourseWorkspaceResult,
  Lecture,
  ManagedCourseWorkspaceResult,
} from "./types";

type ApiLecture = {
  id: string;
  title: string;
  date: string;
  access_override?: CourseAccessRule | null;
  material_path?: string | null;
};

type ApiLectureView = {
  lecture: ApiLecture;
  attendance?: Attendance;
  content_ready?: boolean;
  effective_publication_at?: string | null;
  release_status?: LectureReleaseStatus;
  unlocked?: boolean;
};

type ApiCourseWorkspaceResult = Omit<CourseWorkspaceResult, "lectures"> & {
  lectures: ApiLecture[];
  published_lecture_ids?: string[];
};

type ApiManagedCourseWorkspaceResult = ApiCourseWorkspaceResult & {
  access_summary: CourseAccessSummary;
};

export function normalizeCourseWorkspaceResult(
  payload: ApiCourseWorkspaceResult,
): CourseWorkspaceResult {
  return {
    ...payload,
    lectures: payload.lectures.map((lecture) => lectureFromApi(lecture)),
    publishedLectureIds: payload.published_lecture_ids ?? payload.publishedLectureIds ?? [],
  };
}

export function normalizeManagedCourseWorkspaceResult(
  payload: ApiManagedCourseWorkspaceResult,
): ManagedCourseWorkspaceResult {
  return {
    ...normalizeCourseWorkspaceResult(payload),
    accessSummary: payload.access_summary,
  };
}

export function normalizeLectureList(payload: Array<ApiLecture | ApiLectureView>): Lecture[] {
  return payload.map((item) => {
    if ("lecture" in item) {
      return lectureFromApi(item.lecture, item.attendance, item);
    }
    return lectureFromApi(item);
  });
}

function lectureFromApi(
  lecture: ApiLecture,
  attendance: Attendance = "unknown",
  view: ApiLectureView | null = null,
): Lecture {
  return {
    id: lecture.id,
    number: lectureNumber(lecture.id),
    title: lecture.title,
    date: lecture.date,
    attendance,
    accessOverride: lecture.access_override ?? null,
    contentReady: view?.content_ready,
    effectivePublicationAt: view?.effective_publication_at ?? null,
    materialPath: lecture.material_path ?? undefined,
    releaseStatus: view?.release_status,
    unlocked: view?.unlocked,
  };
}

function lectureNumber(lectureId: string) {
  const match = lectureId.match(/(\d+)$/);
  return match ? match[1].padStart(2, "0") : lectureId.replace(/^lecture-/, "");
}
