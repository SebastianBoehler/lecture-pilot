import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";
import { openProfessorDemo } from "./testLessonActions";

describe("Professor course builder generation retry", () => {
  afterEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("retries only the failed lecture after a network failure", async () => {
    const user = userEvent.setup();
    const baseFetch = professorFetchMock();
    const draftAttempts = new Map<string, number>();
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      const lectureId = url.match(/lectures\/(lecture-\d+)\/canvas\/draft/)?.[1];
      if (lectureId && init?.method === "POST") {
        const attempt = (draftAttempts.get(lectureId) ?? 0) + 1;
        draftAttempts.set(lectureId, attempt);
        if (lectureId === "lecture-02" && attempt === 1) {
          return Promise.reject(new TypeError("Failed to fetch"));
        }
      }
      return baseFetch(url, init);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await openProfessorDemo(user);
    await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    await user.upload(
      await screen.findByLabelText(/^choose files$/i),
      new File(["# extra note"], "supplement.md", { type: "text/markdown" }),
    );
    await user.click(screen.getByRole("button", { name: /upload and process materials/i }));
    await screen.findByText(/2 lectures inferred from the source bundle/i);
    await user.click(screen.getByRole("button", { name: /apply lecture schedule/i }));
    await screen.findByRole("heading", { name: /review youtube candidates/i });
    await user.click(screen.getByRole("button", { name: /continue to canvas draft/i }));
    await user.click(screen.getByRole("button", { name: /generate all lecture canvases/i }));

    expect(await screen.findByText(/could not reach the API/i)).toBeInTheDocument();
    expect(screen.queryByText(/^Failed to fetch$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/lecture canvas drafts? failed/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/lecture generation progress/i)).toHaveAttribute(
      "aria-live",
      "polite",
    );
    expect(screen.getByRole("button", { name: /continue to publishing/i })).toBeDisabled();
    expect(draftAttempts).toEqual(
      new Map([
        ["lecture-01", 1],
        ["lecture-02", 1],
      ]),
    );
    const retry = screen.getByRole("button", { name: /retry Lecture 02/i });
    await waitFor(() => expect(retry).toBeEnabled());
    await user.click(retry);

    await waitFor(() => expect(draftAttempts.get("lecture-02")).toBe(2));
    expect(await screen.findByText(/Lecture 02 canvas is ready to review/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /continue to publishing/i })).toBeEnabled();
    await waitFor(() =>
      expect(draftAttempts).toEqual(
        new Map([
          ["lecture-01", 1],
          ["lecture-02", 2],
        ]),
      ),
    );
  });
});
