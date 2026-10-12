import { useCallback, useEffect, useRef, useState } from "react";

import { initialCourseId, localDemoSession } from "../shell/appDefaults";
import type { AppRoute } from "../shell/appRoute";
import { writeDemoWorkspaceCourse } from "../auth/demoWorkspaceAccess";
import { withLocalDemoCourses } from "../auth/localDemoCourses";
import { usePublishedLectures } from "../lesson/usePublishedLectures";
import { findLoadableWorkspaceCourse, type LoadedWorkspaceCourse } from "./workspaceCourseLoader";
import type { Attendance, Lecture, LoginSession, UniversityCourse } from "../shared/types";

/** Owns the student's current course workspace: its course, lectures and publication state. */
export function useCourseWorkspace(
  route: AppRoute,
  session: LoginSession | null,
  setSession: (session: LoginSession) => void,
) {
  const sessionRef = useRef(session);
  useEffect(() => {
    sessionRef.current = session;
  }, [session]);
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [course, setCourse] = useState<UniversityCourse>(localDemoSession.courses[0]);
  const [courseId, setCourseId] = useState(() => initialCourseId(route));
  const [loadError, setLoadError] = useState<string | null>(null);
  const [publishedLectureIds, setPublishedLectureIds] = usePublishedLectures(lectures);

  const showCourse = useCallback((nextCourse: UniversityCourse, nextLectures: Lecture[]) => {
    setCourse(nextCourse);
    setCourseId(nextCourse.id);
    setLectures(nextLectures);
  }, []);

  const load = useCallback(
    async (
      activeSession: LoginSession,
      preferredCourseId: string,
    ): Promise<LoadedWorkspaceCourse | null> => {
      try {
        const loaded = await findLoadableWorkspaceCourse(activeSession, preferredCourseId);
        setLoadError(null);
        if (!loaded) {
          setLectures([]);
          return null;
        }
        setCourse(loaded.course);
        if (sessionRef.current === activeSession) {
          const nextSession = withLocalDemoCourses(activeSession, loaded.courses);
          if (nextSession !== activeSession) setSession(nextSession);
        }
        setCourseId(loaded.course.id);
        setLectures(loaded.lectures);
        return loaded;
      } catch (error) {
        setLectures([]);
        setLoadError(error instanceof Error ? error.message : "Course workspace loading failed.");
        return null;
      }
    },
    [setSession],
  );

  function showPublished(nextCourse: UniversityCourse, nextLectures: Lecture[]) {
    const published = nextLectures.map((lecture) => ({ ...lecture, contentReady: true }));
    writeDemoWorkspaceCourse(nextCourse);
    showCourse(nextCourse, published);
    setLoadError(null);
    setPublishedLectureIds(published.map((lecture) => lecture.id));
    return published;
  }

  function setAttendance(lectureId: string, attendance: Attendance) {
    setLectures((current) =>
      current.map((lecture) => (lecture.id === lectureId ? { ...lecture, attendance } : lecture)),
    );
  }

  function resetAttendance() {
    setLectures((current) => current.map((lecture) => ({ ...lecture, attendance: "unknown" })));
  }

  return {
    course,
    courseId,
    lectures,
    loadError,
    publishedLectureIds,
    load,
    clearLoadError: () => setLoadError(null),
    markPublished: (lectureId: string) =>
      setPublishedLectureIds((current) => Array.from(new Set([...current, lectureId]))),
    clearPublished: () => setPublishedLectureIds([]),
    resetAttendance,
    setAttendance,
    showCourse,
    showPublished,
  };
}

export type CourseWorkspace = ReturnType<typeof useCourseWorkspace>;
