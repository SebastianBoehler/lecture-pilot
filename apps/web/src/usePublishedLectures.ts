import { useEffect, useState } from "react";

import { getCanvasPublication } from "./api";
import type { Lecture, LoginSession } from "./types";

export function usePublishedLectures(
  courseId: string,
  lectures: Lecture[],
  session: LoginSession | null,
) {
  const [publishedLectureIds, setPublishedLectureIds] = useState<string[]>([]);

  useEffect(() => {
    if (!session) {
      setPublishedLectureIds([]);
      return;
    }
    const activeSession = session;
    let cancelled = false;
    async function refreshPublication() {
      const results = await Promise.allSettled(
        lectures.map((lecture) => getCanvasPublication(courseId, lecture.id, activeSession)),
      );
      if (cancelled) return;
      setPublishedLectureIds(
        results
          .map((result, index) => (result.status === "fulfilled" && result.value.published ? lectures[index].id : null))
          .filter((lectureId): lectureId is string => Boolean(lectureId)),
      );
    }
    void refreshPublication();
    return () => {
      cancelled = true;
    };
  }, [courseId, lectures, session]);

  return [publishedLectureIds, setPublishedLectureIds] as const;
}
