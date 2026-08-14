import type { UniversityEnrollmentCourse } from "./universityCourseTypes";

export type CourseSuggestionSource = "alma_timetable" | "ilias_membership" | "alma_catalog";

export type CourseTitleSuggestion = {
  title: string;
  sources: CourseSuggestionSource[];
  number?: string | null;
  instructor?: string | null;
};

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

export function personalCourseSuggestions(
  courses: UniversityEnrollmentCourse[],
  term: string,
): CourseTitleSuggestion[] {
  return mergeCourseSuggestions(
    courses
      .filter((course) => course.term === term && course.title.trim())
      .map((course) => ({
        title: course.title.trim(),
        sources: [
          course.source === "ilias" ? "ilias_membership" : "alma_timetable",
        ] as CourseSuggestionSource[],
        number: course.number,
        instructor: course.instructor,
      })),
  );
}

export function mergeCourseSuggestions(
  suggestions: CourseTitleSuggestion[],
): CourseTitleSuggestion[] {
  const merged = new Map<string, CourseTitleSuggestion>();
  for (const suggestion of suggestions) {
    const title = suggestion.title.trim();
    const key = title.toLocaleLowerCase("de-DE");
    if (!title) continue;
    const current = merged.get(key);
    if (!current) {
      merged.set(key, { ...suggestion, title, sources: [...suggestion.sources] });
      continue;
    }
    current.sources = [...new Set([...current.sources, ...suggestion.sources])];
    current.number ??= suggestion.number;
    current.instructor ??= suggestion.instructor;
  }
  return [...merged.values()];
}
