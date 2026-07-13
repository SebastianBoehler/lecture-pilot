import type { UniversityEnrollmentCourse } from "./universityCourseTypes";

export function universityCourseTitles(courses: UniversityEnrollmentCourse[], term: string) {
  const titles = new Map<string, string>();
  for (const course of courses) {
    const title = course.title.trim();
    if (course.term !== term || !title) continue;
    const key = title.toLocaleLowerCase("de-DE");
    if (!titles.has(key)) titles.set(key, title);
  }
  return [...titles.values()].sort((left, right) =>
    left.localeCompare(right, "de-DE", { sensitivity: "base" }),
  );
}

export function mergeCourseTitles(primary: string[], secondary: string[]) {
  const titles = new Map<string, string>();
  for (const rawTitle of [...primary, ...secondary]) {
    const title = rawTitle.trim();
    const key = title.toLocaleLowerCase("de-DE");
    if (title && !titles.has(key)) titles.set(key, title);
  }
  return [...titles.values()];
}
