import { availableCourseLectures } from "./dashboardCourses";
import type { LearnerCourseProfile, Lecture } from "./types";

export type LectureProgress = { completed: boolean; passed: number; total: number };

export type CourseProgress = {
  byLecture: Map<string, LectureProgress>;
  passed: number;
  total: number;
  percent: number;
};

export function courseProgress(
  lectures: Lecture[],
  profile: LearnerCourseProfile | undefined,
): CourseProgress {
  const passedIds = new Set(profile?.passed_lecture_ids ?? []);
  const counts = new Map(
    (profile?.lecture_progress ?? []).map((item) => [item.lecture_id, item] as const),
  );
  const byLecture = new Map<string, LectureProgress>();
  for (const lecture of lectures) {
    const count = counts.get(lecture.id);
    const completed = passedIds.has(lecture.id);
    if (!completed && !count) continue;
    byLecture.set(lecture.id, {
      completed,
      passed: count?.passed_gates ?? 0,
      total: count?.total_gates ?? 0,
    });
  }
  const available = availableCourseLectures(lectures);
  const passed = available.filter((lecture) => passedIds.has(lecture.id)).length;
  return {
    byLecture,
    passed,
    total: available.length,
    percent: available.length ? Math.round((passed / available.length) * 100) : 0,
  };
}

/** Collapsed list: newest unlocked lectures first, then the next scheduled one. */
export function previewLectures(lectures: Lecture[], count: number): Lecture[] {
  const available = availableCourseLectures(lectures);
  const ordered = available
    .map((lecture, index) => ({ lecture, index, time: Date.parse(lecture.date) }))
    .sort((left, right) =>
      Number.isFinite(left.time) && Number.isFinite(right.time) && left.time !== right.time
        ? right.time - left.time
        : right.index - left.index,
    )
    .slice(0, count)
    .map((item) => item.lecture);
  const nextScheduled = lectures.find((lecture) => lecture.releaseStatus === "scheduled");
  return nextScheduled ? [...ordered, nextScheduled] : ordered;
}
