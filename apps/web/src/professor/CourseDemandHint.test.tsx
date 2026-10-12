import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CourseDemandHint } from "./CourseDemandHint";
import { I18nWrapper, renderWithI18n } from "../test/renderWithI18n";
import type { LoginSession } from "../shared/types";

const professor: LoginSession = {
  username: "prof",
  term: "Sommer 2026",
  roles: ["professor"],
  account_type: "professor",
  auth_transport: "cookie",
  courses: [],
};

afterEach(() => vi.useRealTimers());

function stubMatch(requestCount: number) {
  const fetchMock = vi.fn(
    async (_input: RequestInfo | URL) =>
      new Response(JSON.stringify({ request_count: requestCount, enrolled_user_count: 40 }), {
        headers: { "Content-Type": "application/json" },
      }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function settle(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe("Course demand builder hint", () => {
  it("debounces title input and shows the aggregate request count", async () => {
    vi.useFakeTimers();
    const fetchMock = stubMatch(23);
    const { rerender } = render(
      <CourseDemandHint session={professor} term="Sommer 2026" title="Natural" />,
      { wrapper: I18nWrapper },
    );
    rerender(<CourseDemandHint session={professor} term="Sommer 2026" title="Natural Language" />);
    await settle(450);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const url = new URL(String(fetchMock.mock.calls[0][0]), "http://localhost");
    expect(url.pathname).toBe("/admin/course-support-demand/match");
    expect(url.searchParams.get("title")).toBe("Natural Language");
    expect(url.searchParams.get("term")).toBe("Sommer 2026");
    expect(screen.getByRole("status")).toHaveTextContent(
      "23 students already asked for this course on LecturePilot.",
    );
  });

  it("stays silent without demand or for short titles", async () => {
    vi.useFakeTimers();
    const fetchMock = stubMatch(0);
    const { rerender } = render(
      <CourseDemandHint session={professor} term="Sommer 2026" title="NL" />,
      { wrapper: I18nWrapper },
    );
    await settle(450);
    expect(fetchMock).not.toHaveBeenCalled();

    rerender(<CourseDemandHint session={professor} term="Sommer 2026" title="Data Ethics" />);
    await settle(450);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("uses the German singular wording", async () => {
    vi.useFakeTimers();
    stubMatch(1);
    renderWithI18n(<CourseDemandHint session={professor} term="Sommer 2026" title="Ethik" />, {
      locale: "de",
    });
    await settle(450);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Bereits 1 Person hat diesen Kurs auf LecturePilot angefragt.",
    );
  });
});
