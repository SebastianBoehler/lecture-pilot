import { useEffect, useRef } from "react";

import { canManageCourses } from "./authz";
import type { Attendance, Lecture, LoginSession } from "./types";

export function useInitialDraftPreview({
  availableLectures,
  session,
  onBlocked,
  onOpenLecture,
}: {
  availableLectures: Lecture[];
  session: LoginSession | null;
  onBlocked: () => void;
  onOpenLecture: (
    courseId: string,
    lecture: Lecture,
    backView: "dashboard" | "professor",
    userId: string,
    previewDraft: boolean,
  ) => void;
}) {
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("preview") !== "draft") return;
    if (!session) return;
    handled.current = true;
    if (!canManageCourses(session)) {
      onBlocked();
      return;
    }
    const courseId = params.get("courseId") ?? "martius-ml";
    const lectureId = params.get("lectureId") ?? "lecture-03";
    const lecture = availableLectures.find((item) => item.id === lectureId) ?? {
      id: lectureId,
      number: params.get("lectureNumber") ?? lectureId.replace("lecture-", ""),
      title: params.get("lectureTitle") ?? "Draft lecture",
      date: "Draft",
      attendance: "unknown" as Attendance,
    };
    onOpenLecture(courseId, lecture, "professor", "professor-preview", true);
  }, [availableLectures, onBlocked, onOpenLecture, session]);
}
