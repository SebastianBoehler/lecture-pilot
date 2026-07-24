import { lessonPath } from "./appRoute";
import type { Lecture } from "./types";

export function draftPreviewUrl(courseId: string, lecture: Lecture) {
  return `${window.location.origin}${lessonPath(courseId, lecture.id, "draft")}`;
}
