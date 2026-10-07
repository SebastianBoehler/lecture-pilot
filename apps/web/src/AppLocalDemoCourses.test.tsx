import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { localDemoSession } from "./appDefaults";
import { mockLoginFetch } from "./testFixtures";

describe("local demo course discovery", () => {
  it("opens practice exams with enrollment in an imported local course", async () => {
    const user = userEvent.setup();
    const localCourse = {
      ...localDemoSession.courses[0],
      id: "local-nlp",
      title: "Natural Language Processing",
    };
    const fixtureFetch = mockLoginFetch({ published: true });
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses")) {
        return { ok: true, json: async () => [...localDemoSession.courses, localCourse] };
      }
      if (url.endsWith("/practice-exams") || url.endsWith("/ppi-exam-sources")) {
        return { ok: true, json: async () => [] };
      }
      return fixtureFetch(url, init);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await user.click(screen.getByRole("button", { name: "Preview local demo" }));
    await user.click(
      await screen.findByRole("button", {
        name: "Open Natural Language Processing workspace",
      }),
    );
    await user.click(screen.getByRole("tab", { name: "Practice exams" }));
    expect(await screen.findByText("No practice exams yet.")).toBeVisible();
    await waitFor(() => {
      const examCalls = fetchMock.mock.calls.filter(([url]) =>
        String(url).endsWith("/courses/local-nlp/practice-exams"),
      );
      expect(examCalls.length).toBeGreaterThan(0);
      for (const [, init] of examCalls) {
        expect(new Headers(init?.headers).get("X-Course-Ids")?.split(",")).toContain("local-nlp");
      }
    });
  });
});
