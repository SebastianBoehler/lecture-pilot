import { describe, expect, it } from "vitest";

import { courseUpdatePath, lessonPath, pathForView, readAppRoute } from "./appRoute";

describe("app routes", () => {
  it("maps major views to stable paths", () => {
    expect(pathForView("dashboard")).toBe("/workspaces");
    expect(pathForView("profile")).toBe("/profile");
    expect(pathForView("professor")).toBe("/professor/courses/new");
    expect(pathForView("course-management")).toBe("/professor/courses");
    expect(pathForView("performance")).toBe("/professor/performance");
    expect(pathForView("usage")).toBe("/professor/usage");
    expect(pathForView("how-it-works")).toBe("/how-it-works");
  });

  it("round-trips learner, preview, draft, and course-update routes", () => {
    const learner = lessonPath("machine learning", "lecture-03");
    const preview = lessonPath("machine learning", "lecture-03", "professor-preview");
    const draft = lessonPath("machine learning", "lecture-03", "draft");
    const update = courseUpdatePath("machine learning");

    expect(read(learner)).toEqual({
      view: "lesson",
      courseId: "machine learning",
      lectureId: "lecture-03",
      lessonMode: "learner",
    });
    expect(read(preview)).toMatchObject({ view: "lesson", lessonMode: "professor-preview" });
    expect(read(draft)).toMatchObject({ view: "lesson", lessonMode: "draft" });
    expect(read(update)).toEqual({
      view: "course-management",
      updateCourseId: "machine learning",
    });
  });

  it("keeps old draft-preview links readable during migration", () => {
    expect(
      readAppRoute({
        pathname: "/",
        search: "?preview=draft&courseId=security&lectureId=lecture-01",
      } as Location),
    ).toEqual({
      view: "lesson",
      courseId: "security",
      lectureId: "lecture-01",
      lessonMode: "draft",
    });
  });
});

function read(path: string) {
  const url = new URL(path, "https://lecturepilot.example");
  return readAppRoute({ pathname: url.pathname, search: url.search } as Location);
}
