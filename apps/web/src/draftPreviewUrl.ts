import type { Lecture } from "./types";

export function draftPreviewUrl(courseId: string, lecture: Lecture) {
  const params = new URLSearchParams({
    preview: "draft",
    courseId,
    lectureId: lecture.id,
    lectureNumber: lecture.number,
    lectureTitle: lecture.title,
  });
  return `${window.location.origin}${window.location.pathname}?${params.toString()}`;
}
