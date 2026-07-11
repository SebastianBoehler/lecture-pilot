import { readDemoWorkspaceCourse } from "./demoWorkspaceAccess";
import { hasDevelopmentWorkspaceAccess } from "./devWorkspaceAccess";
import type { Lecture, LoginSession, UniversityCourse } from "./types";
import type { UniversityEnrollmentCourse } from "./universityCourseTypes";

type CourseWorkspaceStatus = "matched" | "unmatched";

export type CourseWorkspaceGroup = {
  course: UniversityCourse;
  status: CourseWorkspaceStatus;
  statusLabel: string;
  tutorAvailable: boolean;
  courseLectures: Lecture[];
};

type CourseGroupLabels = {
  aiTutorAvailable: string;
  noTutor: string;
};

export function buildCourseGroups(
  session: LoginSession | null,
  workspaceCourse: UniversityCourse,
  lectures: Lecture[],
  publishedLectureIds: string[],
  labels: CourseGroupLabels,
): CourseWorkspaceGroup[] {
  // University observations are display-only; only platform courses can authorize tutor access.
  const authorizedCourses = session?.courses ?? [];
  const observedCourses = displayUniversityCourses(session?.university_courses ?? []);
  const enrolledCourses = observedCourses.length ? observedCourses : authorizedCourses;
  const workspaceAuthorized =
    authorizedCourses.some((course) => isWorkspaceCourse(course, workspaceCourse)) ||
    hasWorkspaceAccess(workspaceCourse);
  const courseGroups = enrolledCourses.length
    ? enrolledCourses.map((course) =>
        buildEnrolledCourseGroup(
          course,
          workspaceCourse,
          lectures,
          publishedLectureIds,
          workspaceAuthorized,
          labels,
        ),
      )
    : hasWorkspaceAccess(workspaceCourse)
      ? [buildDiscoverableCourseGroup(workspaceCourse, lectures, publishedLectureIds, labels)]
      : [];

  if (
    enrolledCourses.length &&
    !enrolledCourses.some((course) => isWorkspaceCourse(course, workspaceCourse)) &&
    workspaceAuthorized &&
    publishedLectureIds.length > 0
  ) {
    courseGroups.push(
      buildDiscoverableCourseGroup(workspaceCourse, lectures, publishedLectureIds, labels),
    );
  }
  return courseGroups.sort(
    (left, right) => Number(right.tutorAvailable) - Number(left.tutorAvailable),
  );
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
  workspaceAuthorized: boolean,
  labels: CourseGroupLabels,
): CourseWorkspaceGroup {
  const publishedLectures = publishedCourseLectures(lectures, publishedLectureIds);
  const tutorAvailable =
    workspaceAuthorized &&
    publishedLectures.length > 0 &&
    isWorkspaceCourse(course, workspaceCourse);
  return {
    course: tutorAvailable ? workspaceCourse : course,
    status: tutorAvailable ? "matched" : "unmatched",
    statusLabel: tutorAvailable ? labels.aiTutorAvailable : labels.noTutor,
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

function displayUniversityCourses(courses: UniversityEnrollmentCourse[]): UniversityCourse[] {
  const unique = new Map<string, UniversityCourse>();
  for (const course of courses) {
    const key = `${course.term}:${course.title
      .normalize("NFKC")
      .toLocaleLowerCase("de-DE")
      .replace(/[^\p{L}\p{N}]+/gu, "")}`;
    if (unique.has(key)) continue;
    unique.set(key, {
      id: `university:${course.source}:${course.external_course_id}`,
      title: course.title,
      professor: course.instructor ?? course.organization ?? "University of Tübingen",
      term: course.term,
    });
  }
  return [...unique.values()];
}
