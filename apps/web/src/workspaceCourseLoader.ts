import { getCourseLectures, getCourses } from "./api";
import { findUniversityWorkspaceCourse } from "./dashboardCourses";
import { readDemoWorkspaceCourse } from "./demoWorkspaceAccess";
import { developmentWorkspaceCourse } from "./devWorkspaceAccess";
import type { Lecture, LoginSession, UniversityCourse } from "./types";

export type LoadedWorkspaceCourse = {
  course: UniversityCourse;
  lectures: Lecture[];
};

export async function findLoadableWorkspaceCourse(
  activeSession: LoginSession,
  preferredCourseId: string,
): Promise<LoadedWorkspaceCourse | null> {
  const courses = await getCourses(activeSession);
  const savedDemoCourse = readDemoWorkspaceCourse();
  const candidates = uniqueCourses([
    courses.find((course) => course.id === preferredCourseId),
    courses.find((course) => course.id === savedDemoCourse?.id),
    findUniversityWorkspaceCourse(
      courses,
      activeSession.university_courses ?? [],
      activeSession.courses,
    ),
    developmentWorkspaceCourse(),
    ...[...courses].reverse(),
  ]);
  let successfulReads = 0;
  let lastError: unknown = null;
  for (const course of candidates) {
    try {
      const lectures = await getCourseLectures(course.id, activeSession);
      successfulReads += 1;
      if (lectures.length) return { course, lectures };
    } catch (error) {
      lastError = error;
    }
  }
  if (!successfulReads && lastError) throw lastError;
  return null;
}

function uniqueCourses(courses: Array<UniversityCourse | null | undefined>) {
  return courses.filter(
    (course, index, list): course is UniversityCourse =>
      Boolean(course) && list.findIndex((item) => item?.id === course?.id) === index,
  );
}
