import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DashboardCourseWorkspaces } from "./DashboardCourseWorkspaces";
import { buildCourseGroups } from "./dashboardCourses";
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
    {
      source: "alma",
      external_course_id: "title:nlp",
      term: "Sommer 2026",
      title: "Natural Language Processing",
    },
    {
      source: "ilias",
      external_course_id: "crs:7",
      term: "Sommer 2026",
      title: "Natural Language Processing",
    },
    { source: "ilias", external_course_id: "crs:9", term: "Sommer 2026", title: "Data Ethics" },
  ],
};

const nlp = { source: "alma", external_course_id: "title:nlp", term: "Sommer 2026" };
const ethics = { source: "ilias", external_course_id: "crs:9", term: "Sommer 2026" };

function renderCourses(activeSession: LoginSession = session) {
  const groups = buildCourseGroups(
    activeSession,
    { id: "workspace", title: "Workspace", professor: "", term: "Sommer 2026" },
    [],
    [],
    { aiTutorAvailable: "AI tutor available", noTutor: "Not supported yet" },
  );
  renderWithI18n(
    <DashboardCourseWorkspaces
      courseGroups={groups}
      newLectureIds={new Set()}
      selectedCourseId=""
      session={activeSession}
      onOpen={vi.fn()}
      onOpenSection={vi.fn()}
      onProgress={vi.fn()}
      onSelectCourse={vi.fn()}
      onSetAttendance={vi.fn()}
    />,
  );
}

function stubRequests(items: unknown[]) {
  const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (method === "GET") return json({ items });
    const body = JSON.parse(String(init?.body));
    const requested = method === "PUT";
    return json({ ...body, requested, request_count: requested ? 4 : 3 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function courseItem(title: string) {
  return screen.getByRole("heading", { name: title }).closest("li") as HTMLElement;
}

describe("Course support requests", () => {
  it("requests and withdraws LecturePilot for an observed course", async () => {
    const user = userEvent.setup();
    const fetchMock = stubRequests([
      { ...nlp, requested: false, request_count: 3 },
      { ...ethics, requested: false, request_count: 0 },
    ]);
    renderCourses();

    const item = courseItem("Natural Language Processing");
    expect(await within(item).findByText("3 students asked")).toBeInTheDocument();
    expect(within(courseItem("Data Ethics")).queryByText(/asked/)).not.toBeInTheDocument();

    await user.click(
      within(item).getByRole("button", {
        name: "Request LecturePilot for Natural Language Processing",
      }),
    );
    expect(await within(item).findByText("Requested")).toBeInTheDocument();
    expect(within(item).getByText("You and 3 others asked for this course")).toBeInTheDocument();
    const [, putInit] = fetchMock.mock.calls[1];
    expect(putInit?.method).toBe("PUT");
    expect(JSON.parse(String(putInit?.body))).toEqual(nlp);
    expect(new Headers(putInit?.headers).get("X-CSRF-Token")).toBe("csrf-token");

    await user.click(
      within(item).getByRole("button", {
        name: "Withdraw LecturePilot request for Natural Language Processing",
      }),
    );
    expect(await within(item).findByText("3 students asked")).toBeInTheDocument();
    expect(fetchMock.mock.calls[2][1]?.method).toBe("DELETE");
  });

  it("shows the solo wording and a retryable error", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) =>
        (init?.method ?? "GET") === "GET"
          ? json({ items: [{ ...ethics, requested: true, request_count: 1 }] })
          : json({ detail: "Database unavailable." }, 503),
      ),
    );
    renderCourses();

    const item = courseItem("Data Ethics");
    expect(await within(item).findByText("You asked for this course")).toBeInTheDocument();
    await user.click(within(item).getByRole("button", { name: /Withdraw LecturePilot request/ }));
    expect(await within(item).findByRole("alert")).toHaveTextContent(
      "Your request could not be saved.",
    );
    expect(within(item).getByText("Requested")).toBeInTheDocument();
  });

  it("does not offer requests to non-student sessions", () => {
    const fetchMock = stubRequests([]);
    renderCourses({ ...session, roles: ["professor"] });
    expect(screen.queryByRole("button", { name: /Request LecturePilot/ })).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

function json(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
