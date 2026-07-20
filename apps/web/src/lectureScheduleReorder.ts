import type { LectureScheduleItem } from "./types";

export function reorderLectureSchedule(
  schedule: LectureScheduleItem[],
  fromIndex: number,
  toIndex: number,
) {
  if (
    fromIndex === toIndex ||
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= schedule.length ||
    toIndex >= schedule.length
  ) {
    return schedule;
  }
  const reordered = [...schedule];
  const [moved] = reordered.splice(fromIndex, 1);
  reordered.splice(toIndex, 0, moved);
  const width = Math.max(2, String(reordered.length).length);
  return reordered.map((lecture, index) => ({
    ...lecture,
    number: String(index + 1).padStart(width, "0"),
  }));
}
