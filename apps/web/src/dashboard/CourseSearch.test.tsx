import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "./Dashboard";
import { renderWithI18n } from "../test/renderWithI18n";
import type { Lecture, LoginSession, UniversityCourse } from "../shared/types";

afterEach(() => vi.unstubAllGlobals());

const course: UniversityCourse = {
  id: "search-course",
  title: "Search course",
  professor: "Professor",
  term: "2026",
};

const lectures: Lecture[] = [
  {
    id: "lecture-01",
    number: "01",
    title: "Bayes",
    date: "2026-04-01",
    attendance: "unknown",
    releaseStatus: "released",
  },
];

const session: LoginSession = {
  username: "student-a",
  tenant_id: "tenant-tuebingen",
  term: "2026",
  roles: ["student"],
  courses: [course],
};

function renderSearch(onOpen = vi.fn()) {
  renderWithI18n(
    <Dashboard
      lectures={lectures}
      publishedLectureIds={["lecture-01"]}
      session={session}
      workspaceCourse={course}
      onOpen={onOpen}
      onSetAttendance={vi.fn()}
    />,
  );
  return onOpen;
}

describe("Course search", () => {
  it("searches unlocked lectures and opens the matching section in the app", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/search?")) {
        return json({
          truncated: false,
          results: [
            {
              lecture_id: "lecture-01",
              lecture_title: "Bayes",
              section_id: "posterior",
              section_title: "Posterior",
              snippet: "…the posterior combines prior and likelihood…",
            },
          ],
        });
      }
      return json({ course_id: course.id, items: [], upcoming: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    const onOpen = renderSearch();

    const input = screen.getByRole("searchbox", { name: "Search Search course" });
    await user.type(input, "p");
    expect(screen.queryByText("Searching…")).not.toBeInTheDocument();
    await user.type(input, "osterior");

    const result = await screen.findByRole("button", { name: "Open Posterior in Bayes" });
    expect(result).toHaveTextContent("the posterior combines prior and likelihood");
    const searchCalls = fetchMock.mock.calls.filter(([url]) => String(url).includes("/search?"));
    expect(searchCalls).toHaveLength(1);
    expect(String(searchCalls[0][0])).toContain("/courses/search-course/search?q=posterior");

    await user.click(result);
    expect(onOpen).toHaveBeenCalledWith(course.id, lectures[0], undefined, "posterior");
  });

  it("explains empty and failed searches", async () => {
    const user = userEvent.setup();
    let fail = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (!String(input).includes("/search?")) {
          return json({ course_id: course.id, items: [], upcoming: [] });
        }
        return fail
          ? new Response(JSON.stringify({ detail: "nope" }), { status: 500 })
          : json({ truncated: false, results: [] });
      }),
    );
    renderSearch();

    const input = screen.getByRole("searchbox");
    await user.type(input, "zebra");
    expect(await screen.findByText("No matches in unlocked lectures.")).toBeVisible();
    fail = true;
    await user.type(input, "s");
    expect(await screen.findByText("Search failed. Try again.")).toHaveAttribute("role", "alert");
  });
});

function json(value: unknown) {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
