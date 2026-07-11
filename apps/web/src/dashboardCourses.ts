import { readDemoWorkspaceCourse } from "./demoWorkspaceAccess";
import { hasDevelopmentWorkspaceAccess } from "./devWorkspaceAccess";
import type { Lecture, LoginSession, UniversityCourse } from "./types";

type CourseWorkspaceStatus = "matched" | "unmatched";

export type CourseWorkspaceGroup = {
  course: UniversityCourse;
  status: CourseWorkspaceStatus;
  statusLabel: string;
  emptyText: string;
  tutorAvailable: boolean;
  courseLectures: Lecture[];
};

type CourseGroupLabels = {
  aiTutorAvailable: string;
  noMatchedTutor: string;
  noTutor: string;
  publishToEnable: string;
};

export function buildCourseGroups(
  session: LoginSession | null,
  workspaceCourse: UniversityCourse,
  lectures: Lecture[],
  publishedLectureIds: string[],
  labels: CourseGroupLabels,
): CourseWorkspaceGroup[] {
  const enrolledCourses = session?.courses ?? [];
  const courseGroups = enrolledCourses.length
    ? enrolledCourses.map((course) =>
        buildEnrolledCourseGroup(course, workspaceCourse, lectures, publishedLectureIds, labels),
      )
    : hasWorkspaceAccess(workspaceCourse)
      ? [buildDiscoverableCourseGroup(workspaceCourse, lectures, publishedLectureIds, labels)]
      : [];

  if (
    enrolledCourses.length &&
    !enrolledCourses.some((course) => isWorkspaceCourse(course, workspaceCourse)) &&
    hasWorkspaceAccess(workspaceCourse) &&
    publishedLectureIds.length > 0
  ) {
    courseGroups.push(
      buildDiscoverableCourseGroup(workspaceCourse, lectures, publishedLectureIds, labels),
    );
  }
  return courseGroups;
}

export function publishedCourseLectures(lectures: Lecture[], publishedLectureIds: string[]) {
  const published = new Set(publishedLectureIds);
  return lectures.filter((lecture) => published.has(lecture.id));
}

function buildEnrolledCourseGroup(
  course: UniversityCourse,
  workspaceCourse: UniversityCourse,
  lectures: Lecture[],
  publishedLectureIds: string[],
  labels: CourseGroupLabels,
): CourseWorkspaceGroup {
  const publishedLectures = publishedCourseLectures(lectures, publishedLectureIds);
  const tutorAvailable = publishedLectures.length > 0 && isWorkspaceCourse(course, workspaceCourse);
  return {
    course,
    status: tutorAvailable ? "matched" : "unmatched",
    statusLabel: tutorAvailable ? labels.aiTutorAvailable : labels.noTutor,
    emptyText: labels.noMatchedTutor,
    tutorAvailable,
    courseLectures: tutorAvailable ? publishedLectures : [],
  };
}

function buildDiscoverableCourseGroup(
  workspaceCourse: UniversityCourse,
  lectures: Lecture[],
  publishedLectureIds: string[],
  labels: CourseGroupLabels,
): CourseWorkspaceGroup {
  const publishedLectures = publishedCourseLectures(lectures, publishedLectureIds);
  const tutorAvailable = publishedLectures.length > 0;
  return {
    course: workspaceCourse,
    status: tutorAvailable ? "matched" : "unmatched",
    statusLabel: tutorAvailable ? labels.aiTutorAvailable : labels.noTutor,
    emptyText: labels.publishToEnable,
    tutorAvailable,
    courseLectures: publishedLectures,
  };
}

function isWorkspaceCourse(course: UniversityCourse, workspaceCourse: UniversityCourse) {
  return (
    course.id === workspaceCourse.id ||
    normalizeCourseTitle(course.title) === normalizeCourseTitle(workspaceCourse.title)
  );
}

function hasWorkspaceAccess(workspaceCourse: UniversityCourse) {
  return (
    readDemoWorkspaceCourse()?.id === workspaceCourse.id ||
    hasDevelopmentWorkspaceAccess(workspaceCourse)
  );
}

function normalizeCourseTitle(title: string) {
  return title.toLowerCase().replace(/\s+/g, " ").trim();
}
