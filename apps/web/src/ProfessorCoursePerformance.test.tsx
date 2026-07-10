import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProfessorCoursePerformance } from "./ProfessorCoursePerformance";
import { renderWithI18n } from "./test/renderWithI18n";

describe("ProfessorCoursePerformance", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("does not render zero-percent charts when a published lecture has no learner activity", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => json(noActivityAnalytics())));

    renderWithI18n(
      <ProfessorCoursePerformance
        lectures={[lecture()]}
        publishedLectureIds={["lecture-01"]}
        session={session()}
        workspaceCourse={course()}
      />,
    );

    expect(await screen.findByText(/no learner signals yet/i)).toBeInTheDocument();
    expect(screen.queryByLabelText("Lecture analytics chart")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /learning path gates/i })).not.toBeInTheDocument();
  });
});

function json(payload: unknown) {
  return { ok: true, json: async () => payload };
}

function course() {
  return {
    id: "demo-ml-course",
    professor: "professor-demo",
    term: "Summer 2026",
    title: "Demo ML Course",
  };
}

function lecture() {
  return {
    attendance: "unknown" as const,
    date: "2026-05-09",
    id: "lecture-01",
    number: "01",
    title: "Introduction",
  };
}

function noActivityAnalytics() {
  return {
    course_id: "demo-ml-course",
    gates: [],
    lecture_id: "lecture-01",
    quizzes: [],
    total_events: 0,
  };
}

function session() {
  return {
    courses: [course()],
    roles: ["professor" as const],
    term: "Summer 2026",
    username: "professor-demo",
  };
}
