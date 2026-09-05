import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DashboardCourseWorkspaces } from "./DashboardCourseWorkspaces";
import { renderWithI18n } from "./test/renderWithI18n";

describe("Dashboard study tool loading", () => {
  it("loads exam data only on first use and retains it across tab switches", async () => {
    const fetchMock = vi.fn(async () => ({ ok: true, json: async () => [] }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    const course = { id: "course-1", title: "Learning", professor: "Professor", term: "2026" };
    renderWithI18n(
      <DashboardCourseWorkspaces
        courseGroups={[
          {
            course,
            courseLectures: [],
            sources: [],
            tutorAvailable: true,
            status: "matched",
            statusLabel: "AI tutor available",
          },
        ]}
        session={{ username: "student", term: "2026", courses: [course] }}
        onOpen={vi.fn()}
        onProgress={vi.fn()}
        onSetAttendance={vi.fn()}
      />,
    );

    expect(fetchMock).not.toHaveBeenCalled();
    await user.click(screen.getByRole("tab", { name: "Practice exams" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/courses/course-1/practice-exams"),
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/courses/course-1/ppi-exam-sources"),
      expect.any(Object),
    );
    await user.click(screen.getByRole("tab", { name: "Lectures" }));
    await user.click(screen.getByRole("tab", { name: "Practice exams" }));
    expect(screen.getByRole("button", { name: "Generate exam" })).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
