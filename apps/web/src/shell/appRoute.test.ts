import { describe, expect, it } from "vitest";

import { coursePagePath, lessonPath, pathForView, readAppRoute } from "./appRoute";

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

  it("round-trips learner, preview, draft, and course page routes", () => {
    const learner = lessonPath("machine learning", "lecture-03");
    const preview = lessonPath("machine learning", "lecture-03", "professor-preview");
    const draft = lessonPath("machine learning", "lecture-03", "draft");
    const course = coursePagePath("machine learning");

    expect(read(learner)).toEqual({
      view: "lesson",
      courseId: "machine learning",
      lectureId: "lecture-03",
      lessonMode: "learner",
    });
    expect(read(preview)).toMatchObject({ view: "lesson", lessonMode: "professor-preview" });
    expect(read(draft)).toMatchObject({ view: "lesson", lessonMode: "draft" });
    expect(read(course)).toEqual({ view: "course-management", courseId: "machine learning" });
    expect(read("/professor/courses")).toEqual({ view: "course-management" });
    expect(read("/professor/courses/new")).toEqual({ view: "professor" });
  });
});

function read(path: string) {
  const url = new URL(path, "https://lecturepilot.example");
  return readAppRoute({ pathname: url.pathname });
}
