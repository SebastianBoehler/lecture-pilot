import { describe, expect, it } from "vitest";

import { mergeCourseTitles, universityCourseTitles } from "./professorCourseSuggestions";

describe("professor course suggestions", () => {
  it("returns unique, sorted titles from available university sources", () => {
    expect(
      universityCourseTitles(
        [
          {
            source: "ilias",
            external_course_id: "crs:2",
            term: "Sommer 2026",
            title: "  Systems  ",
          },
          {
            source: "alma",
            external_course_id: "title:ml",
            term: "Sommer 2026",
            title: "Machine Learning",
          },
          {
            source: "ilias",
            external_course_id: "crs:3",
            term: "Sommer 2026",
            title: "Algorithms",
          },
          {
            source: "ilias",
            external_course_id: "crs:4",
            term: "Sommer 2026",
            title: "Systems",
          },
          {
            source: "ilias",
            external_course_id: "crs:5",
            term: "Winter 2025/26",
            title: "Old Course",
          },
        ],
        "Sommer 2026",
      ),
    ).toEqual(["Algorithms", "Machine Learning", "Systems"]);
  });

  it("keeps personal course titles ahead of public Alma suggestions", () => {
    expect(
      mergeCourseTitles(
        ["Personal Systems", "Machine Learning"],
        ["machine learning", "Public Course"],
      ),
    ).toEqual(["Personal Systems", "Machine Learning", "Public Course"]);
  });
});
