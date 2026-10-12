import { screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { ProfessorCourseManager } from "./ProfessorCourseManager";
import { renderWithI18n } from "../test/renderWithI18n";

function manager(isLoading: boolean) {
  return (
    <ProfessorCourseManager
      deletingCourseId={null}
      isLoading={isLoading}
      onCreateCourse={vi.fn()}
      onDeleteCourse={vi.fn()}
      onManageCourseAccess={vi.fn()}
      onManageLectureAccess={vi.fn()}
      onRefresh={vi.fn()}
      onPreviewLecture={vi.fn()}
      onResumeCourse={vi.fn()}
      onShareCourse={vi.fn()}
      onUpdateCourse={vi.fn()}
      session={{ username: "professor-demo", term: "2026", courses: [] }}
      workspaces={[]}
    />
  );
}

it("shows a loading state, not 'no courses', while the course list loads", () => {
  const loading = renderWithI18n(manager(true));
  expect(screen.getByRole("status")).toHaveTextContent("Loading your courses…");
  expect(screen.queryByText("No created course workspaces yet.")).not.toBeInTheDocument();
  loading.unmount();

  renderWithI18n(manager(false));
  expect(screen.getByText("No created course workspaces yet.")).toBeInTheDocument();
});
