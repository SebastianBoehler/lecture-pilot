import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";
import { openProfessorDemo } from "./testLessonActions";
import type { CourseSourceRoutingManifest, YoutubeVideoCandidate } from "./types";

describe("Professor lecture media search", () => {
  afterEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("updates suggested and manual searches with the selected lecture", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", professorFetchMock());
    render(<App />);

    await openProfessorDemo(user);
    await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    await user.upload(
      await screen.findByLabelText(/^choose files$/i),
      new File(["# lecture one"], "Lecture01-eng.tex", { type: "application/x-tex" }),
    );
    await user.click(screen.getByRole("button", { name: /upload and process materials/i }));
    await user.click(await screen.findByRole("button", { name: /apply lecture schedule/i }));
    await screen.findByRole("heading", { name: /source assignments ready/i });
    await user.click(screen.getByRole("button", { name: /accept assignments and continue/i }));

    const target = screen.getByLabelText(/choose videos for/i);
    const suggestions = screen.getByRole("region", { name: /suggested searches/i });
    expect(target).toHaveValue("lecture-01");
    expect(within(suggestions).getAllByText(/Lecture 01/).length).toBeGreaterThan(0);
    const firstLectureVideo = await screen.findByLabelText(/bayesian decision theory/i);
    await user.click(firstLectureVideo);
    expect(await screen.findByText(/saved 1 approved video for lecture 01/i)).toBeInTheDocument();

    await user.selectOptions(target, "lecture-02");

    await waitFor(() => {
      expect(within(suggestions).getAllByText(/Lecture 02/).length).toBeGreaterThan(0);
      expect((screen.getByLabelText(/search query/i) as HTMLInputElement).value).toContain(
        "Lecture 02",
      );
    });
    expect(within(suggestions).queryAllByText(/Lecture 01/)).toHaveLength(0);
    expect(await screen.findByLabelText(/bayesian decision theory/i)).not.toBeChecked();

    await user.selectOptions(target, "lecture-01");
    await waitFor(() => {
      expect(screen.getByLabelText(/bayesian decision theory/i)).toBeChecked();
    });
  });

  it("reports the total persisted selection count after approving multiple videos", async () => {
    const user = userEvent.setup();
    const baseFetch = professorFetchMock();
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      const response = await baseFetch(url, init);
      if (!url.includes("/media/youtube/search")) return response;
      const payload = (await response.json()) as { items: YoutubeVideoCandidate[] };
      const first = payload.items[0];
      return {
        ok: true,
        json: async () => ({
          items: [
            first,
            {
              ...first,
              video_id: "secondVideo1",
              title: "A second machine-learning explanation",
              url: "https://www.youtube.com/watch?v=secondVideo1",
            },
          ],
        }),
      };
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await openProfessorDemo(user);
    await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    await user.upload(
      await screen.findByLabelText(/^choose files$/i),
      new File(["# lecture one"], "Lecture01-eng.tex", { type: "application/x-tex" }),
    );
    await user.click(screen.getByRole("button", { name: /upload and process materials/i }));
    await user.click(await screen.findByRole("button", { name: /apply lecture schedule/i }));
    await screen.findByRole("heading", { name: /source assignments ready/i });
    await user.click(screen.getByRole("button", { name: /accept assignments and continue/i }));

    await user.click(await screen.findByLabelText(/bayesian decision theory/i));
    await user.click(await screen.findByLabelText(/second machine-learning explanation/i));

    expect(await screen.findByText(/saved 2 approved videos for lecture 01/i)).toBeInTheDocument();
  });

  it("returns to source review when routing is no longer confirmed", async () => {
    const user = userEvent.setup();
    const baseFetch = professorFetchMock();
    let routingInvalidated = false;
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      const response = await baseFetch(url, init);
      const path = new URL(url, "http://localhost").pathname;
      if (routingInvalidated && path.endsWith("/source-routing") && !init?.method) {
        const payload = (await response.json()) as CourseSourceRoutingManifest;
        return { ok: true, json: async () => ({ ...payload, confirmed: false }) };
      }
      return response;
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await openProfessorDemo(user);
    await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    await user.upload(
      await screen.findByLabelText(/^choose files$/i),
      new File(["# lecture one"], "Lecture01-eng.tex", { type: "application/x-tex" }),
    );
    await user.click(screen.getByRole("button", { name: /upload and process materials/i }));
    await user.click(await screen.findByRole("button", { name: /apply lecture schedule/i }));
    await screen.findByRole("heading", { name: /source assignments ready/i });
    await user.click(screen.getByRole("button", { name: /accept assignments and continue/i }));
    await screen.findByRole("heading", { name: /review youtube candidates/i });

    routingInvalidated = true;
    await user.click(screen.getByRole("button", { name: /continue to canvas draft/i }));

    expect(await screen.findByRole("heading", { name: /source assignments ready/i })).toBeVisible();
    expect(
      screen.queryByRole("heading", { name: /generate canvas draft/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/review and confirm source assignments again/i)).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) => String(url).includes("/canvas/draft") && init?.method === "POST",
      ),
    ).toBe(false);
  });
});
