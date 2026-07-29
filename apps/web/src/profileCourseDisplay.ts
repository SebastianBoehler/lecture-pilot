import type { UniversityCourse } from "./types";

export function findProfileCourse(courseId: string, courses: UniversityCourse[]) {
  return courses.find((course) => {
    const titleSlug = courseSlug(course.title);
    return (
      course.id === courseId || titleSlug === courseId || differsByOneCharacter(titleSlug, courseId)
    );
  });
}

export function humanizeCourseId(courseId: string) {
  return courseId
    .split(/[-_]+/)
    .filter(Boolean)
    .map((word) => word[0]?.toUpperCase() + word.slice(1))
    .join(" ");
}

function courseSlug(title: string) {
  return title
    .normalize("NFKD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function differsByOneCharacter(left: string, right: string) {
  if (Math.abs(left.length - right.length) > 1) return false;
  const [shorter, longer] = left.length <= right.length ? [left, right] : [right, left];
  let shortIndex = 0;
  let longIndex = 0;
  let differences = 0;
  while (shortIndex < shorter.length && longIndex < longer.length) {
    if (shorter[shortIndex] === longer[longIndex]) {
      shortIndex += 1;
      longIndex += 1;
      continue;
    }
    differences += 1;
    if (differences > 1) return false;
    if (shorter.length === longer.length) shortIndex += 1;
    longIndex += 1;
  }
  return differences + (longIndex < longer.length ? 1 : 0) <= 1;
}
