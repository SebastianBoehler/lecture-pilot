import { useEffect, useState } from "react";

import type { Lecture } from "./types";

export function usePublishedLectures(lectures: Lecture[]) {
  const [publishedLectureIds, setPublishedLectureIds] = useState<string[]>([]);

  useEffect(() => {
    if (lectures.length === 0) {
      setPublishedLectureIds([]);
      return;
    }
    if (lectures.some((lecture) => lecture.contentReady === undefined)) return;
    setPublishedLectureIds(
      lectures.filter((lecture) => lecture.contentReady).map((lecture) => lecture.id),
    );
  }, [lectures]);

  return [publishedLectureIds, setPublishedLectureIds] as const;
}
