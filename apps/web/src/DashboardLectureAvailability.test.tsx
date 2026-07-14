import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Dashboard } from "./Dashboard";
import { I18nProvider } from "./i18n";
import type { Lecture, LoginSession, UniversityCourse } from "./types";

const course: UniversityCourse = {
  id: "access-course",
  title: "Access Course",
  professor: "Prof. Access",
  term: "Sommer 2026",
};

const session: LoginSession = {
  username: "student",
  term: "Sommer 2026",
  courses: [course],
};

const lectures: Lecture[] = [
  {
    id: "lecture-01",
    number: "01",
    title: "Available lecture",
    date: "2026-07-01",
    attendance: "unknown",
    contentReady: true,
    releaseStatus: "released",
    unlocked: true,
  },
  {
    id: "lecture-02",
    number: "02",
    title: "Scheduled lecture",
    date: "2099-07-18",
    attendance: "unknown",
    contentReady: true,
    effectivePublicationAt: "2099-07-17T22:00:00Z",
    releaseStatus: "scheduled",
    unlocked: false,
  },
];

describe("Dashboard lecture availability", () => {
  it("shows a scheduled placeholder without learner actions", () => {
    render(
      <I18nProvider locale="en" setLocale={vi.fn()}>
        <Dashboard
          lectures={lectures}
          publishedLectureIds={lectures.map((lecture) => lecture.id)}
          session={session}
          workspaceCourse={course}
          onOpen={vi.fn()}
          onSetAttendance={vi.fn()}
        />
      </I18nProvider>,
    );

    const scheduled = screen.getByRole("heading", { name: "Scheduled lecture" }).closest("article");
    expect(scheduled).not.toBeNull();
    expect(within(scheduled!).getByText(/available .*2099/i)).toBeVisible();
    expect(within(scheduled!).queryByRole("button")).not.toBeInTheDocument();
    expect(within(scheduled!).queryByRole("group")).not.toBeInTheDocument();

    const available = screen.getByRole("heading", { name: "Available lecture" }).closest("article");
    expect(available).not.toBeNull();
    expect(within(available!).getByRole("button", { name: /open lecture 01/i })).toBeEnabled();
    expect(within(available!).getByRole("group", { name: /attendance for available/i })).toBeVisible();
  });

  it("shows a server-authorized course even when it is not in the enrollment snapshot", () => {
    const otherCourse: UniversityCourse = {
      id: "other-course",
      title: "Other Course",
      professor: "Prof. Other",
      term: "Sommer 2026",
    };

    render(
      <I18nProvider locale="en" setLocale={vi.fn()}>
        <Dashboard
          lectures={lectures}
          publishedLectureIds={lectures.map((lecture) => lecture.id)}
          session={{ ...session, courses: [otherCourse] }}
          workspaceCourse={course}
          onOpen={vi.fn()}
          onSetAttendance={vi.fn()}
        />
      </I18nProvider>,
    );

    expect(screen.getByRole("heading", { name: "Access Course" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Scheduled lecture" })).toBeVisible();
  });
});
