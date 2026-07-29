import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LearnerCourseFiles } from "./LearnerCourseFiles";
import { renderWithI18n } from "./test/renderWithI18n";

describe("LearnerCourseFiles", () => {
  it("groups legacy title-slug files under the human course name", () => {
    renderWithI18n(
      <LearnerCourseFiles
        courses={[
          {
            id: "martius-ml",
            title: "Grundlagen des Maschinellen Lernens",
            professor: "Prof. Georg Martius",
            term: "Sommer 2026",
          },
        ]}
        profiles={[
          {
            course_id: "martius-ml",
            memory: "",
            passed_lecture_ids: [],
            files: [{ path: "summary.md", size_bytes: 12, content: "Summary" }],
          },
          {
            course_id: "grundlagen-des-machinellen-lernens",
            memory: "",
            passed_lecture_ids: [],
            files: [{ path: "notes.md", size_bytes: 10, content: "Notes" }],
          },
        ]}
      />,
    );

    expect(screen.getByText("Grundlagen des Maschinellen Lernens")).toBeInTheDocument();
    expect(screen.getByText("2 files")).toBeInTheDocument();
    expect(screen.queryByText("grundlagen-des-machinellen-lernens")).not.toBeInTheDocument();
  });
});
