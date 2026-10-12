import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CourseDemandPage } from "./CourseDemandPage";
import { AppHeader } from "../shell/AppHeader";
import { pathForView, readAppRoute } from "../shell/appRoute";
import { renderWithI18n } from "../test/renderWithI18n";
import type { LoginSession, TenantRole } from "../shared/types";

const admin: LoginSession = {
  username: "admin",
  term: "Sommer 2026",
  roles: ["student", "tenant_admin"],
  account_type: "student",
  auth_transport: "cookie",
  courses: [],
};

const row = {
  source: "alma",
  external_course_id: "title:nlp",
  term: "Sommer 2026",
  title: "Natural Language Processing",
  number: "INFO4193",
  organization: "Fachbereich Informatik",
  instructor: "Prof. Example",
  display_url: "https://alma.uni-tuebingen.de/course/42",
  request_count: 23,
  enrolled_user_count: 41,
  has_workspace: false,
  first_requested_at: "2026-10-01T08:00:00Z",
  last_requested_at: "2026-10-11T08:00:00Z",
};

function stubDemand(payload: unknown, status = 200) {
  const fetchMock = vi.fn(
    async (_input: RequestInfo | URL) =>
      new Response(JSON.stringify(payload), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("Course demand page", () => {
  it("lists aggregate demand with an external Alma link", async () => {
    const fetchMock = stubDemand({
      items: [
        row,
        {
          ...row,
          source: "ilias",
          external_course_id: "crs:9",
          title: "Data Ethics",
          number: null,
          instructor: null,
          display_url: "javascript:alert(1)",
          request_count: 0,
          enrolled_user_count: 5,
          has_workspace: true,
          first_requested_at: null,
          last_requested_at: null,
        },
      ],
    });
    renderWithI18n(<CourseDemandPage session={admin} />);

    const table = await screen.findByRole("table");
    const [, first, second] = within(table).getAllByRole("row");
    expect(within(first).getByRole("rowheader")).toHaveTextContent("Natural Language Processing");
    expect(within(first).getByText("23")).toBeInTheDocument();
    expect(within(first).getByText("41")).toBeInTheDocument();
    const link = within(first).getByRole("link", { name: "Open in Alma" });
    expect(link).toHaveAttribute("href", row.display_url);
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(within(second).queryByRole("link")).not.toBeInTheDocument();
    expect(within(second).getByText("Linked workspace")).toBeInTheDocument();
    expect(String(fetchMock.mock.calls[0][0])).toContain("/platform/course-support-demand");
  });

  it("reports backend refusals", async () => {
    stubDemand({ detail: "Platform administrator access is required." }, 403);
    renderWithI18n(<CourseDemandPage session={admin} />, { locale: "de" });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Platform administrator access is required.",
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Kursnachfrage");
  });
});

describe("Course demand navigation", () => {
  it.each([
    [["student", "tenant_admin"], true],
    [["professor", "tenant_admin"], true],
    [["professor"], false],
    [["student"], false],
  ] as [TenantRole[], boolean][])("roles %j show the entry: %s", (roles, visible) => {
    const onOpenCourseDemand = vi.fn();
    renderWithI18n(
      <AppHeader
        activeView="dashboard"
        session={{
          ...admin,
          roles,
          account_type: roles.includes("professor") ? "professor" : "student",
        }}
        theme="light"
        onBrand={vi.fn()}
        onOpenCourseDemand={onOpenCourseDemand}
        onOpenCourseManagement={vi.fn()}
        onOpenDashboard={vi.fn()}
        onOpenFeedback={vi.fn()}
        onOpenPerformance={vi.fn()}
        onOpenProfessor={vi.fn()}
        onOpenProfile={vi.fn()}
        onOpenUsage={vi.fn()}
        onToggleTheme={vi.fn()}
      />,
    );
    const entry = screen.queryByRole("button", { name: "Course demand" });
    expect(Boolean(entry)).toBe(visible);
    entry?.click();
    expect(onOpenCourseDemand).toHaveBeenCalledTimes(visible ? 1 : 0);
  });

  it("routes the platform path to the demand view", () => {
    expect(pathForView("course-demand")).toBe("/platform/course-demand");
    expect(readAppRoute({ pathname: "/platform/course-demand" })).toEqual({
      view: "course-demand",
    });
  });
});
