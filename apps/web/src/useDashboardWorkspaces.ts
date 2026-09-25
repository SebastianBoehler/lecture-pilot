import { useEffect, useState } from "react";

import { getCourseLectures, getCourses } from "./api";
import type { LoadedCourseWorkspace } from "./dashboardCourses";
import type { Attendance, LoginSession } from "./types";

export function useDashboardWorkspaces(session: LoginSession | null, primaryCourseId: string) {
  const [workspaces, setWorkspaces] = useState<LoadedCourseWorkspace[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) {
      setWorkspaces([]);
      setError(null);
      return;
    }
    let cancelled = false;
    async function load() {
      try {
        const courses = await getCourses(session!);
        const additional = await Promise.all(
          courses.filter((course) => course.id !== primaryCourseId).map(async (course) => {
            const lectures = await getCourseLectures(course.id, session!);
            return {
              course,
              lectures,
              publishedLectureIds: lectures
                .filter((lecture) => lecture.contentReady)
                .map((lecture) => lecture.id),
            };
          }),
        );
        if (!cancelled) {
          setWorkspaces(additional);
          setError(null);
        }
      } catch (cause) {
        if (!cancelled) {
          setWorkspaces([]);
          setError(cause instanceof Error ? cause.message : "Course loading failed.");
        }
      }
    }
    void load();
    return () => { cancelled = true; };
  }, [session, primaryCourseId]);

  function setAttendance(courseId: string, lectureId: string, attendance: Attendance) {
    setWorkspaces((current) => current.map((workspace) =>
      workspace.course.id === courseId
        ? {
            ...workspace,
            lectures: workspace.lectures.map((lecture) =>
              lecture.id === lectureId ? { ...lecture, attendance } : lecture,
            ),
          }
        : workspace,
    ));
  }

  return { workspaces, error, setAttendance };
}
