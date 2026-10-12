import { lessonPath } from "../shell/appRoute";
import type { Lecture } from "../shared/types";

export function draftPreviewUrl(courseId: string, lecture: Lecture) {
  return `${window.location.origin}${lessonPath(courseId, lecture.id, "draft")}`;
}
