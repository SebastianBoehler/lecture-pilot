import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { localProfessorSession } from "../shell/appDefaults";
import { renderWithI18n } from "../test/renderWithI18n";
import { courseWorkspace, json, lecture, mockApi, states } from "./coursePageTestFixtures";
import { ProfessorCourseManagement } from "./ProfessorCourseManagement";

afterEach(() => vi.unstubAllGlobals());

const listed = {
  course: courseWorkspace.course,
  lectures: courseWorkspace.lectures,
  active_lecture_id: courseWorkspace.active_lecture_id,
  access_summary: courseWorkspace.accessSummary,
};

function render(courseId?: string) {
  const onOpenCourse = vi.fn();
  renderWithI18n(
    <ProfessorCourseManagement
      courseId={courseId}
      onCreateCourse={vi.fn()}
      onResumeCourse={vi.fn()}
      onOpenCourse={onOpenCourse}
      onWorkspaceDeleted={vi.fn()}
      session={localProfessorSession}
    />,
  );
  return onOpenCourse;
}

describe("Course management and the course page", () => {
  it("opens a published course instead of offering a separate update page", async () => {
    mockApi({ "GET /admin/courses": () => json([listed]) });
    const user = userEvent.setup();
    const onOpenCourse = render();
    await user.click(await screen.findByRole("button", { name: "Open Machine Learning" }));
    expect(onOpenCourse).toHaveBeenCalledWith("machine-learning");
    expect(screen.queryByRole("button", { name: "Update" })).not.toBeInTheDocument();
  });

  it("renders the course page for a course route", async () => {
    mockApi({
      "GET /admin/courses": () => json([listed]),
      "GET /lecture-states": () => json(states([lecture("lecture-01")])),
    });
    render("machine-learning");
    expect(await screen.findByRole("heading", { name: "Machine Learning" })).toBeInTheDocument();
    expect(await screen.findByText("1 lecture, 1 published")).toBeInTheDocument();
  });

  it("says when a course route does not match a managed course", async () => {
    mockApi({ "GET /admin/courses": () => json([listed]) });
    render("unknown-course");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This course was not found, or you no longer manage it.",
    );
  });
});
