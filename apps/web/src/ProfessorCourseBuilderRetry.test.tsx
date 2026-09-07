import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";
import {
  approveAllLearningDesigns,
  approveAllPracticeDesigns,
  openProfessorDemo,
} from "./testLessonActions";

describe("Professor course builder generation retry", () => {
  afterEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it.each([
    { terminal: false, regenerate: false },
    { terminal: true, regenerate: false },
    { terminal: true, regenerate: true },
  ])(
    "recovers only the failed lecture (terminal: $terminal, regeneration: $regenerate)",
    async ({ terminal, regenerate }) => {
      const user = userEvent.setup();
      const baseFetch = professorFetchMock();
      const draftAttempts = new Map<string, number>();
      const requestKeys = new Map<string, string[]>();
      let releaseRetry: (() => void) | undefined;
      const retryPause = new Promise<void>((resolve) => {
        releaseRetry = resolve;
      });
      const fetchMock = vi.fn((url: string, init?: RequestInit) => {
        const lectureId = url.match(/lectures\/(lecture-\d+)\/canvas\/draft/)?.[1];
        if (lectureId && init?.method === "POST") {
          const attempt = (draftAttempts.get(lectureId) ?? 0) + 1;
          draftAttempts.set(lectureId, attempt);
          requestKeys.set(lectureId, [
            ...(requestKeys.get(lectureId) ?? []),
            new Headers(init.headers).get("Idempotency-Key") ?? "",
          ]);
          if (lectureId === "lecture-02" && attempt === (regenerate ? 2 : 1)) {
            if (terminal)
              return Promise.resolve(
                new Response(JSON.stringify({ detail: "Repair needed." }), {
                  status: 503,
                  headers: {
                    "Content-Type": "application/json",
                    "X-Generation-Status": "failed",
                    "X-Generation-Repairable": "true",
                  },
                }),
              );
            return Promise.reject(new TypeError("Failed to fetch"));
          }
        }
        if (
          terminal &&
          !regenerate &&
          lectureId === "lecture-02" &&
          init?.method === "POST" &&
          draftAttempts.get(lectureId) === 2
        ) {
          return retryPause.then(() => baseFetch(url, init));
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
      await screen.findByRole("heading", { name: /source assignments ready/i });
      await user.click(screen.getByRole("button", { name: /accept assignments and continue/i }));
      await user.click(
        await screen.findByRole("button", {
          name: /continue (?:without videos|to learning plan)/i,
        }),
      );
      await screen.findByRole("heading", { name: /learning goals/i });
      await approveAllPracticeDesigns(user);

      if (regenerate) {
        await screen.findByText(/2 lecture canvases ready to review/i);
        await user.click(screen.getByRole("button", { name: /regenerate draft canvas/i }));
      }

      if (terminal) {
        if (!regenerate)
          expect(
            await screen.findByText(/1 lecture canvases ready to review/i),
          ).toBeInTheDocument();
        await screen.findByRole("button", { name: /continue unfinished lectures/i });
        if (!regenerate) {
          await user.click(screen.getByRole("button", { name: /review lecture canvas for 01/i }));
          await user.click(
            await screen.findByRole("button", { name: /approve canvas for publication/i }),
          );
          await screen.findByText("1 of 2 approved");
          fetchMock.mockClear();
        }
        await user.click(screen.getByRole("button", { name: /continue unfinished lectures/i }));
        if (!regenerate) {
          await waitFor(() => expect(draftAttempts.get("lecture-02")).toBe(2));
          expect(screen.getByText("1 of 2 approved")).toBeInTheDocument();
          expect(
            fetchMock.mock.calls.some(([url]) => url.includes("lecture-01/canvas/learning-design")),
          ).toBe(false);
          releaseRetry?.();
        }
        await screen.findByText(/2 lecture canvases ready to review/i);
        expect(
          fetchMock.mock.calls.some(([url]) => url.endsWith("lecture-02/canvas/draft/repair")),
        ).toBe(true);
      }

      await screen.findByText(/2 lecture canvases ready to review/i, {}, { timeout: 3000 });
      expect(screen.queryByText(/could not reach the API/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/^Failed to fetch$/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/lecture canvas drafts? failed/i)).not.toBeInTheDocument();
      expect(screen.getAllByText("Needs review")[0]).toHaveAttribute("aria-live", "polite");
      expect(draftAttempts).toEqual(
        new Map([
          ["lecture-01", regenerate ? 2 : 1],
          ["lecture-02", regenerate ? 3 : 2],
        ]),
      );
      expect(requestKeys.get("lecture-02")).toHaveLength(regenerate ? 3 : 2);
      expect(new Set(requestKeys.get("lecture-02"))).toHaveLength(
        regenerate ? 3 : terminal ? 2 : 1,
      );
      expect(await screen.findByText(/2 lecture canvases ready to review/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/lecture generation progress/i)).toHaveTextContent(
        /Lecture 02/i,
      );
      expect(screen.getByLabelText(/lecture generation progress/i)).toHaveTextContent(
        /needs review/i,
      );
      if (terminal && !regenerate) {
        await user.click(screen.getByRole("button", { name: /review lecture canvas for 02/i }));
        await user.click(
          await screen.findByRole("button", { name: /approve canvas for publication/i }),
        );
        await screen.findByText("2 of 2 approved");
      } else await approveAllLearningDesigns(user);
      expect(screen.getByRole("button", { name: /publish .*tutor workspace/i })).toBeEnabled();
    },
    // Includes cold App loading, every builder stage, and the bounded network retry.
    10_000,
  );
});
