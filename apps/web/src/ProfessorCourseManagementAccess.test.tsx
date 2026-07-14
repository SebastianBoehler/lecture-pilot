import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { localProfessorSession } from "./appDefaults";
import { ProfessorCourseManagement } from "./ProfessorCourseManagement";
import { renderWithI18n } from "./test/renderWithI18n";
import type { CourseAccessRule } from "./courseAccessTypes";

describe("professor course access management", () => {
  it("shows access summaries and sends exact course PUT and lecture DELETE requests", async () => {
    const user = userEvent.setup();
    let defaultRule: CourseAccessRule = {
      audience: "tuebingen_enrolled",
      publication_mode: "on_lecture_date",
      publication_at: null,
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input), "http://localhost").pathname;
      if (path === "/admin/courses" && !init?.method) return json([workspace(defaultRule)]);
      if (path === "/admin/courses/machine-learning/access" && init?.method === "PUT") {
        defaultRule = JSON.parse(String(init.body)).rule;
        return json({ default_rule: defaultRule });
      }
      if (
        path === "/admin/courses/machine-learning/lectures/lecture-01/access" &&
        init?.method === "DELETE"
      ) {
        return json({ rule_source: "course_default", rule: defaultRule });
      }
      throw new Error(`Unexpected request: ${init?.method ?? "GET"} ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderWithI18n(
      <ProfessorCourseManagement
        onCreateCourse={() => undefined}
        onWorkspaceDeleted={() => undefined}
        session={localProfessorSession}
      />,
    );

    expect(await screen.findByText(/Default access: Course participants/)).toBeInTheDocument();
    expect(
      screen.getByText("Published").closest(".created-lecture-access-status"),
    ).toHaveTextContent("Published · Course participants");
    expect(screen.getByText(/Available 18 Jul 2026, 02:00/)).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Manage default access for Machine Learning" }),
    );
    const courseDialog = screen.getByRole("dialog", { name: "Default lecture access" });
    await user.click(within(courseDialog).getByRole("radio", { name: /Instructors only/i }));
    await user.click(within(courseDialog).getByRole("button", { name: "Save access" }));

    const coursePut = fetchMock.mock.calls.find(
      ([url, init]) => String(url).endsWith("/machine-learning/access") && init?.method === "PUT",
    );
    expect(JSON.parse(String(coursePut?.[1]?.body))).toEqual({
      rule: {
        audience: "instructors_only",
        publication_mode: "on_lecture_date",
        publication_at: null,
      },
      confirm_university_members: false,
    });
    expect(
      await screen.findByText("Default access saved for Machine Learning."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Published").closest(".created-lecture-access-status"),
    ).toHaveTextContent("Published · Instructors only");
    expect(screen.getByText("Hidden from students")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Manage access for Introduction" }));
    const lectureDialog = screen.getByRole("dialog", { name: "Access for Introduction" });
    expect(
      within(lectureDialog).getByRole("checkbox", { name: "Use course default" }),
    ).toBeChecked();
    await user.click(within(lectureDialog).getByRole("button", { name: "Save access" }));

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/lectures/lecture-01/access"),
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});

function workspace(defaultRule: CourseAccessRule) {
  const privateAudience = defaultRule.audience === "instructors_only";
  return {
    course: {
      id: "machine-learning",
      title: "Machine Learning",
      professor: "Prof. Demo",
      term: "Sommer 2026",
      access_policy: defaultRule.audience,
      default_publication_mode: defaultRule.publication_mode,
    },
    lectures: [
      {
        id: "lecture-01",
        course_id: "machine-learning",
        title: "Introduction",
        date: "2026-07-18",
      },
    ],
    active_lecture_id: "lecture-01",
    published_lecture_ids: ["lecture-01"],
    access_summary: {
      course_id: "machine-learning",
      default_rule: defaultRule,
      lectures: [
        {
          lecture_id: "lecture-01",
          rule_source: "course_default",
          rule: defaultRule,
          effective_publication_at: privateAudience ? null : "2026-07-18T00:00:00Z",
          release_status: privateAudience ? "hidden" : "scheduled",
          content_ready: true,
        },
      ],
    },
  };
}

function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
