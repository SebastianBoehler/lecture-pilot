import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProfessorCourseAccessDialog } from "./ProfessorCourseAccessDialog";
import { renderWithI18n } from "./test/renderWithI18n";
import type { ManagedCourseWorkspaceResult } from "./types";

describe("ProfessorCourseAccessDialog", () => {
  it("requires explicit confirmation for university-wide course access", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    renderWithI18n(
      <ProfessorCourseAccessDialog
        error={null}
        saving={false}
        target={{ kind: "course", triggerId: "course-trigger", workspace: workspace() }}
        onClose={() => undefined}
        onSave={onSave}
      />,
    );
    const dialog = screen.getByRole("dialog", { name: "Default lecture access" });

    await user.click(within(dialog).getByRole("radio", { name: /University members/i }));
    const save = within(dialog).getByRole("button", { name: "Save access" });
    expect(save).toBeDisabled();
    await user.click(within(dialog).getByRole("checkbox", { name: /every university member/i }));
    await user.click(save);

    expect(onSave).toHaveBeenCalledWith({
      confirmUniversityMembers: true,
      inheritCourseDefault: false,
      rule: {
        audience: "platform_authenticated",
        publication_mode: "on_lecture_date",
        publication_at: null,
      },
    });
  });

  it("restores inheritance by saving the course-default toggle", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    const targetWorkspace = workspace("lecture_override");
    renderWithI18n(
      <ProfessorCourseAccessDialog
        error={null}
        saving={false}
        target={{
          kind: "lecture",
          lecture: targetWorkspace.lectures[0],
          triggerId: "lecture-trigger",
          workspace: targetWorkspace,
        }}
        onClose={() => undefined}
        onSave={onSave}
      />,
    );
    const dialog = screen.getByRole("dialog", { name: "Access for Introduction" });
    const inherit = within(dialog).getByRole("checkbox", { name: "Use course default" });

    expect(inherit).not.toBeChecked();
    await user.click(inherit);
    expect(within(dialog).getByRole("radio", { name: /Course participants/i })).toBeDisabled();
    await user.click(within(dialog).getByRole("button", { name: "Save access" }));

    expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ inheritCourseDefault: true }));
  });
});

function workspace(
  source: "course_default" | "lecture_override" = "course_default",
): ManagedCourseWorkspaceResult {
  const rule = {
    audience: "tuebingen_enrolled" as const,
    publication_mode: "on_lecture_date" as const,
    publication_at: null,
  };
  return {
    course: {
      id: "machine-learning",
      title: "Machine Learning",
      professor: "Prof. Demo",
      term: "Sommer 2026",
      access_policy: "tuebingen_enrolled",
      default_publication_mode: "on_lecture_date",
    },
    lectures: [
      {
        id: "lecture-01",
        number: "01",
        title: "Introduction",
        date: "2026-07-18",
        attendance: "unknown",
      },
    ],
    active_lecture_id: "lecture-01",
    publishedLectureIds: ["lecture-01"],
    accessSummary: {
      course_id: "machine-learning",
      default_rule: rule,
      lectures: [
        {
          lecture_id: "lecture-01",
          rule_source: source,
          rule,
          effective_publication_at: "2026-07-17T22:00:00Z",
          release_status: "scheduled",
          content_ready: true,
        },
      ],
    },
  };
}
