import { readDemoWorkspaceCourse } from "./demoWorkspaceAccess";
import { hasDevelopmentWorkspaceAccess } from "./devWorkspaceAccess";
import type { Lecture, LoginSession, UniversityCourse } from "./types";
import type { UniversityEnrollmentCourse } from "./universityCourseTypes";

type CourseWorkspaceStatus = "matched" | "unmatched";
type CourseSource = UniversityEnrollmentCourse["source"];

type DisplayUniversityCourse = {
  course: UniversityCourse;
  sources: CourseSource[];
};

export type CourseWorkspaceGroup = {
  course: UniversityCourse;
  sources: CourseSource[];
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
  const enrolledCourses = observedCourses.length
    ? observedCourses
    : authorizedCourses.map((course) => ({ course, sources: [] }));
  const workspaceAuthorized =
    lectures.length > 0 ||
    authorizedCourses.some((course) => isWorkspaceCourse(course, workspaceCourse)) ||
    hasWorkspaceAccess(workspaceCourse);
  const courseGroups = enrolledCourses.length
    ? enrolledCourses.map(({ course, sources }) =>
        buildEnrolledCourseGroup(
          course,
          sources,
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
    !enrolledCourses.some(({ course }) => isWorkspaceCourse(course, workspaceCourse)) &&
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

export function availableCourseLectures(lectures: Lecture[]) {
  return lectures.filter(
    (lecture) => lecture.releaseStatus !== "scheduled" && lecture.releaseStatus !== "hidden",
  );
}

function buildEnrolledCourseGroup(
  course: UniversityCourse,
  sources: CourseSource[],
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
    sources,
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
    sources: [],
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

function displayUniversityCourses(
  courses: UniversityEnrollmentCourse[],
): DisplayUniversityCourse[] {
  const unique = new Map<string, DisplayUniversityCourse>();
  for (const course of courses) {
    const key = `${course.term}:${course.title
      .normalize("NFKC")
      .toLocaleLowerCase("de-DE")
      .replace(/[^\p{L}\p{N}]+/gu, "")}`;
    const existing = unique.get(key);
    if (existing) {
      if (!existing.sources.includes(course.source)) {
        existing.sources.push(course.source);
      }
      continue;
    }
    unique.set(key, {
      course: {
        id: `university:${course.source}:${course.external_course_id}`,
        title: course.title,
        professor: course.instructor ?? course.organization ?? "University of Tübingen",
        term: course.term,
      },
      sources: [course.source],
    });
  }
  return [...unique.values()];
}
