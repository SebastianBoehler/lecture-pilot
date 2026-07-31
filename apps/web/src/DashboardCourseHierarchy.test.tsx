import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Dashboard } from "./Dashboard";
import { renderWithI18n } from "./test/renderWithI18n";
import type { Lecture, LoginSession, UniversityCourse } from "./types";

const course: UniversityCourse = {
  access_policy: "tuebingen_enrolled",
  id: "software-quality",
  title: "Softwarequalität in Theorie und Industrieller Praxis",
  professor: "University of Tübingen",
  term: "Sommer 2026",
};

const session: LoginSession = {
  username: "student",
  display_name: "Student",
  email: "student@example.test",
  term: "Sommer 2026",
  roles: ["student"],
  courses: [course],
};

const lectures: Lecture[] = [
  {
    attendance: "unknown",
    date: "2026-04-14",
    id: "lecture-01",
    number: "01",
    title: "Einführung und Kursüberblick",
  },
  {
    attendance: "present",
    date: "2026-04-21",
    id: "lecture-02",
    number: "02",
    title: "Testing Basics",
  },
];

describe("Dashboard supported course hierarchy", () => {
  it("separates course selection from one task-focused workspace", async () => {
    const user = userEvent.setup();
    renderWithI18n(
      <Dashboard
        lectures={lectures}
        publishedLectureIds={lectures.map((lecture) => lecture.id)}
        session={session}
        workspaceCourse={course}
        onOpen={vi.fn()}
        onSetAttendance={vi.fn()}
      />,
    );

    const workspace = screen.getByRole("region", {
      name: `Study workspace for ${course.title}`,
    });
    const courseCard = screen.getByRole("button", {
      name: `Open ${course.title} workspace`,
    });
    expect(courseCard).toHaveAttribute("aria-pressed", "true");

    const tabs = within(workspace).getByRole("tablist", { name: "Study tools" });
    const lecturesTab = within(tabs).getByRole("tab", { name: "Lectures" });
    const readinessTab = within(tabs).getByRole("tab", { name: "Exam check" });
    const practiceTab = within(tabs).getByRole("tab", { name: "Practice exams" });
    expect(lecturesTab).toHaveAttribute("aria-selected", "true");
    expect(
      within(workspace).getByLabelText(`Available lectures for ${course.title}`),
    ).toBeVisible();
    expect(within(workspace).getAllByRole("article")).toHaveLength(2);
    expect(
      within(workspace).getByLabelText(`Exam readiness check for ${course.title}`),
    ).not.toBeVisible();

    lecturesTab.focus();
    await user.keyboard("{ArrowRight}");
    expect(readinessTab).toHaveFocus();
    expect(readinessTab).toHaveAttribute("aria-selected", "true");
    expect(
      within(workspace).getByLabelText(`Exam readiness check for ${course.title}`),
    ).toBeVisible();
    expect(
      within(workspace).getByLabelText(`Available lectures for ${course.title}`),
    ).not.toBeVisible();

    await user.click(practiceTab);
    expect(practiceTab).toHaveAttribute("aria-selected", "true");
    expect(within(workspace).getByLabelText(`Practice exams for ${course.title}`)).toBeVisible();
  });
});
