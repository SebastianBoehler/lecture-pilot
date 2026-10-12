import { useCallback, useEffect, useMemo, useState } from "react";

import { recordCourseVisit, recordLectureVisit } from "./studyApi";
import type { LoginSession } from "../shared/types";

type VisitSnapshot = { key: string; newLectureIds: string[] };

/** Records a course visit for learners and tracks lectures published since the previous one. */
export function useCourseVisit(courseId: string, session: LoginSession | null) {
  const enabled = Boolean(session?.roles?.includes("student") && courseId);
  const key =
    enabled && session ? `${session.tenant_id ?? ""}:${session.username}:${courseId}` : "";
  const [snapshot, setSnapshot] = useState<VisitSnapshot>({ key: "", newLectureIds: [] });

  useEffect(() => {
    if (!key || !session) return;
    let active = true;
    recordCourseVisit(courseId, session)
      .then((visit) => {
        if (active && visit) setSnapshot({ key, newLectureIds: visit.new_lecture_ids });
      })
      // Badges are optional context; a failed visit must never block the dashboard.
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [courseId, key, session]);

  const markOpened = useCallback(
    (lectureCourseId: string, lectureId: string) => {
      if (!session?.roles?.includes("student")) return;
      setSnapshot((current) => ({
        ...current,
        newLectureIds: current.newLectureIds.filter((id) => id !== lectureId),
      }));
      void recordLectureVisit(lectureCourseId, lectureId, session).catch(() => undefined);
    },
    [session],
  );

  const newLectureIds = useMemo(
    () => new Set(snapshot.key === key ? snapshot.newLectureIds : []),
    [key, snapshot],
  );
  return { newLectureIds, markOpened };
}
