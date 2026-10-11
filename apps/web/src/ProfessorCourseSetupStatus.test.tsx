import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import { localProfessorSession } from "./appDefaults";
import { ProfessorCourseManagement } from "./ProfessorCourseManagement";
import { renderWithI18n } from "./test/renderWithI18n";

const rule = {
  audience: "tuebingen_enrolled",
  publication_mode: "on_lecture_date",
  publication_at: null,
};

function course(id: string, title: string, ready: boolean[]) {
  const lectures = ready.map((_, index) => ({
    id: `lecture-0${index + 1}`,
    course_id: id,
    title: `Lecture ${index + 1}`,
    date: "2026-07-18",
  }));
  return {
    course: { id, title, professor: "Prof. Demo", term: "Sommer 2026" },
    lectures,
    active_lecture_id: lectures[0]?.id ?? "",
    access_summary: {
      course_id: id,
      default_rule: rule,
      lectures: lectures.map((lecture, index) => ({
        lecture_id: lecture.id,
        rule_source: "course_default",
        rule,
        effective_publication_at: "2026-07-18T00:00:00Z",
        release_status: "scheduled",
        content_ready: ready[index],
      })),
    },
  };
}

afterEach(() => vi.unstubAllGlobals());

it("labels setup progress and resumes only unfinished courses", async () => {
  const user = userEvent.setup();
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      Response.json([
        course("draft", "Draft course", [false, false]),
        course("partial", "Partial course", [true, false]),
        course("live", "Live course", [true, true]),
      ]),
    ),
  );
  const resume = vi.fn();
  renderWithI18n(
    <ProfessorCourseManagement
      onCreateCourse={() => undefined}
      onResumeCourse={resume}
      onWorkspaceDeleted={() => undefined}
      session={localProfessorSession}
    />,
  );

  expect(await screen.findByText("Setup incomplete")).toBeInTheDocument();
  expect(screen.getByText("1 of 2 lectures published")).toBeInTheDocument();
  expect(screen.getByText("Published")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Continue setting up Live course" })).toBeNull();
  expect(screen.getAllByRole("button", { name: "Update" })).toHaveLength(2);

  await user.click(screen.getByRole("button", { name: "Continue setting up Draft course" }));
  expect(resume.mock.calls[0][0].course.id).toBe("draft");
});
