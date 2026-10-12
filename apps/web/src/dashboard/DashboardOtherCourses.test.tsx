import { screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { DashboardCourseWorkspaces } from "./DashboardCourseWorkspaces";
import { buildCourseGroups, type CourseWorkspaceGroup } from "./dashboardCourses";
import { lectures } from "./testLectureFixture";
import { renderWithI18n } from "../test/renderWithI18n";
import type { LoginSession } from "../shared/types";

const session: LoginSession = {
  username: "student-a",
  term: "Sommer 2026",
  roles: ["student"],
  auth_transport: "cookie",
  csrf_token: "csrf-token",
  courses: [],
  university_courses: [
    { source: "ilias", external_course_id: "crs:9", term: "Sommer 2026", title: "Data Ethics" },
  ],
};

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderGroups(groups: CourseWorkspaceGroup[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json({ items: [] })),
  );
  renderWithI18n(
    <DashboardCourseWorkspaces
      courseGroups={groups}
      newLectureIds={new Set()}
      selectedCourseId=""
      session={session}
      onOpen={vi.fn()}
      onOpenSection={vi.fn()}
      onProgress={vi.fn()}
      onSelectCourse={vi.fn()}
      onSetAttendance={vi.fn()}
    />,
  );
}

function unsupportedGroups() {
  return buildCourseGroups(
    session,
    { id: "workspace", title: "Workspace", professor: "", term: "Sommer 2026" },
    [],
    [],
    { aiTutorAvailable: "AI tutor available", noTutor: "Not supported yet" },
  );
}

function otherCourses() {
  return screen.getByText("Other enrolled courses").closest("details");
}

it("opens other enrolled courses when none of the learner's courses has a tutor yet", () => {
  renderGroups(unsupportedGroups());

  expect(otherCourses()).toHaveAttribute("open");
});

it("keeps other enrolled courses collapsed when a tutor course is available", () => {
  const supported: CourseWorkspaceGroup = {
    course: { id: "ml", title: "Machine Learning", professor: "", term: "Sommer 2026" },
    sources: [],
    status: "matched",
    statusLabel: "AI tutor available",
    tutorAvailable: true,
    courseLectures: lectures,
  };
  renderGroups([supported, ...unsupportedGroups()]);

  expect(otherCourses()).not.toHaveAttribute("open");
});
